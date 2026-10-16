"""
Win32 Window styling and Global Hotkey listener
"""
import ctypes
from ctypes import wintypes
import threading
from app.constants import (
    GWL_EXSTYLE,
    WS_EX_LAYERED,
    WS_EX_TRANSPARENT,
    WS_EX_TOOLWINDOW,
    WS_EX_APPWINDOW,
    SWP_CLICKTHROUGH_REFRESH,
    MOD_NOREPEAT,
    VK_F8,
)

user32 = ctypes.windll.user32

# SetWindowPos HWND insert-after
HWND_TOPMOST = -1
# GetSystemMetrics virtual desktop
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79


def _get_exstyle(hwnd):
    """Đọc extended style dưới dạng unsigned 32-bit (tránh số âm từ GetWindowLongW)."""
    return user32.GetWindowLongW(hwnd, GWL_EXSTYLE) & 0xFFFFFFFF


def _set_exstyle(hwnd, style):
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style & 0xFFFFFFFF)


def _refresh_frame(hwnd):
    """Ép Windows áp dụng lại hit-test / non-client sau khi đổi extended style."""
    user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, SWP_CLICKTHROUGH_REFRESH)


def resolve_tk_hwnds(tk_window_or_hwnd):
    """
    Trả về (child_hwnd, top_hwnd) cho cửa sổ Tk.
    Nhận tk widget (có winfo_id) hoặc HWND int sẵn.
    """
    if hasattr(tk_window_or_hwnd, "winfo_id"):
        child = int(tk_window_or_hwnd.winfo_id())
    else:
        child = int(tk_window_or_hwnd)
    top = user32.GetParent(child) or user32.GetAncestor(child, 2) or child
    return child, top


def get_virtual_screen_rect():
    """Hình chữ nhật desktop ảo (mọi monitor): (x, y, width, height)."""
    try:
        return (
            int(user32.GetSystemMetrics(SM_XVIRTUALSCREEN)),
            int(user32.GetSystemMetrics(SM_YVIRTUALSCREEN)),
            int(user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)),
            int(user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)),
        )
    except Exception:
        return (0, 0, 1920, 1080)


def force_topmost(tk_window):
    """Ép cửa sổ luôn trên cùng bằng Win32 (ổn định hơn attributes sau sleep/fullscreen)."""
    try:
        _, top = resolve_tk_hwnds(tk_window)
        if not top:
            return
        # SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
        user32.SetWindowPos(top, HWND_TOPMOST, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)
    except Exception:
        pass


def is_window_visible_win32(tk_window):
    """True nếu HWND toplevel đang IsWindowVisible."""
    try:
        _, top = resolve_tk_hwnds(tk_window)
        return bool(top and user32.IsWindowVisible(top))
    except Exception:
        return True


def hide_from_taskbar(tk_window):
    """
    Ẩn cửa sổ khỏi taskbar và danh sách Alt+Tab.

    Với cửa sổ Tkinter đã đặt overrideredirect(True), Windows mặc định đã là WS_POPUP
    và không có nút trên taskbar. Hàm này chỉ đảm bảo gắn WS_EX_TOOLWINDOW và gỡ
    WS_EX_APPWINDOW một cách an toàn mà không gọi user32.ShowWindow (SW_HIDE/SW_SHOWNA),
    tránh làm hỏng DWM composite buffer của Tkinter (gây ra màn hình đen) hoặc vô tình
    ẩn nhầm cửa sổ chính khi bong bóng thoại/dialog con xuất hiện.
    """
    try:
        tk_window.update_idletasks()
        _, hwnd = resolve_tk_hwnds(tk_window)
        if not hwnd:
            return

        style = _get_exstyle(hwnd)
        new_style = (style | WS_EX_TOOLWINDOW) & ~WS_EX_APPWINDOW
        if new_style != style:
            _set_exstyle(hwnd, new_style)
    except Exception:
        pass


def set_click_through(hwnd, enable=True):
    """
    Bật/tắt xuyên chuột (WS_EX_TRANSPARENT).

    Chỉ gắn lên HWND wrapper toplevel — KHÔNG đụng HWND con Tk.
    Gắn + SetWindowPos(FRAMECHANGED) lên child làm đơ PhotoImage (mascot đứng hình).
    Hit-test Windows đi từ toplevel nên chỉ cần wrapper.
    """
    try:
        _, top_hwnd = resolve_tk_hwnds(hwnd)
        if not top_hwnd:
            return False

        style = _get_exstyle(top_hwnd)
        if enable:
            new_style = style | WS_EX_LAYERED | WS_EX_TRANSPARENT
        else:
            new_style = (style | WS_EX_LAYERED) & ~WS_EX_TRANSPARENT

        if new_style != style:
            _set_exstyle(top_hwnd, new_style)
            # FRAMECHANGED 1 lần trên wrapper thôi — đủ để hit-test cập nhật
            _refresh_frame(top_hwnd)

        got = _get_exstyle(top_hwnd)
        return bool(got & WS_EX_TRANSPARENT) == bool(enable)
    except Exception:
        return False


def is_click_through_active(hwnd):
    """True nếu wrapper toplevel đang có WS_EX_TRANSPARENT."""
    try:
        _, top = resolve_tk_hwnds(hwnd)
        return bool(_get_exstyle(top) & WS_EX_TRANSPARENT)
    except Exception:
        return False


class GlobalHotkeyManager:
    """
    Quản lý phím tắt toàn hệ thống (Global Hotkey) bằng Windows API RegisterHotKey.
    Đảm bảo phím F8 (hoặc các phím tắt khác) hoạt động ngay cả khi cửa sổ đang ở chế độ
    xuyên chuột và không có focus bàn phím.
    """
    HOTKEY_ID_F8 = 1088

    def __init__(self, on_f8_pressed=None):
        self.on_f8_pressed = on_f8_pressed
        self._thread = None
        self._thread_id = None
        self._running = False
        self.f8_registered = False

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._hotkey_loop, daemon=True)
        self._thread.start()

    def _hotkey_loop(self):
        self._thread_id = ctypes.windll.kernel32.GetCurrentThreadId()
        # Register F8 without modifiers, with MOD_NOREPEAT to avoid repeat key spam
        registered = user32.RegisterHotKey(None, self.HOTKEY_ID_F8, MOD_NOREPEAT, VK_F8)
        if not registered:
            # Fallback without MOD_NOREPEAT for older Windows versions
            registered = user32.RegisterHotKey(None, self.HOTKEY_ID_F8, 0, VK_F8)
        self.f8_registered = bool(registered)

        msg = wintypes.MSG()
        while self._running:
            # GetMessage blocks until a message arrives
            ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if ret <= 0:
                break
            if msg.message == 0x0312:  # WM_HOTKEY
                if msg.wParam == self.HOTKEY_ID_F8:
                    if self.on_f8_pressed:
                        try:
                            self.on_f8_pressed()
                        except Exception:
                            pass
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        user32.UnregisterHotKey(None, self.HOTKEY_ID_F8)
        self.f8_registered = False

    def stop(self):
        self._running = False
        if self._thread_id:
            try:
                user32.PostThreadMessageW(self._thread_id, 0x0012, 0, 0)  # WM_QUIT
            except Exception:
                pass
        if self._thread and self._thread.is_alive():
            try:
                self._thread.join(timeout=0.05)
            except Exception:
                pass


def activate_existing_floating_clock():
    """
    Tìm cửa sổ Floating Clock đang chạy (kể cả bị ẩn/mờ) rồi hiện + đưa lên trên.
    Dùng khi user mở lại trong lúc single-instance đang chặn process mới.
    """
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def _enum(hwnd, _lparam):
        try:
            if not user32.IsWindow(hwnd):
                return True
            length = user32.GetWindowTextLengthW(hwnd)
            title = ""
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                title = buf.value or ""
            # Title do root.title() — vẫn có trên HWND wrapper dù overrideredirect
            if "Floating" in title and "Clock" in title:
                found.append(hwnd)
        except Exception:
            pass
        return True

    try:
        user32.EnumWindows(_enum, 0)
    except Exception:
        return False

    if not found:
        return False

    SW_SHOW = 5
    SW_RESTORE = 9
    for hwnd in found:
        try:
            user32.ShowWindow(hwnd, SW_RESTORE)
            user32.ShowWindow(hwnd, SW_SHOW)
            # HWND_TOPMOST, NOMOVE|NOSIZE|SHOWWINDOW
            user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0040)
            user32.SetForegroundWindow(hwnd)
        except Exception:
            pass
    return True


class SingleInstanceMutex:
    """
    Quản lý Named Mutex của Windows để đảm bảo chỉ có duy nhất một tiến trình
    Floating Clock chạy tại một thời điểm (chống chạy trùng nhiều bản cùng lúc).
    """
    MUTEX_NAME = "Local\\TopFloatingClock_SingleInstance_Mutex"

    def __init__(self):
        self._mutex = None
        self._kernel32 = ctypes.windll.kernel32

    def is_already_running(self):
        # 183 = ERROR_ALREADY_EXISTS trong Win32 API
        self._mutex = self._kernel32.CreateMutexW(None, False, self.MUTEX_NAME)
        last_error = self._kernel32.GetLastError()
        if last_error == 183:
            if self._mutex:
                try:
                    self._kernel32.CloseHandle(self._mutex)
                except Exception:
                    pass
                self._mutex = None
            return True
        return False

    def release(self):
        if self._mutex:
            try:
                self._kernel32.CloseHandle(self._mutex)
            except Exception:
                pass
            self._mutex = None

