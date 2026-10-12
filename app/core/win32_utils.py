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
    MOD_NOREPEAT,
    VK_F8,
)

user32 = ctypes.windll.user32


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
        child = tk_window.winfo_id()
        hwnd = user32.GetParent(child) or user32.GetAncestor(child, 2) or child
        if not hwnd:
            return

        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE) & 0xFFFFFFFF
        new_style = (style | WS_EX_TOOLWINDOW) & ~WS_EX_APPWINDOW
        if new_style != style:
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new_style)
    except Exception:
        pass


def set_click_through(hwnd, enable=True):
    """Bật/tắt tính năng xuyên chuột (WS_EX_TRANSPARENT) cho cửa sổ (cả wrapper và top-level)"""
    try:
        top_hwnd = user32.GetAncestor(hwnd, 2) or user32.GetParent(hwnd) or hwnd
        for h in set([hwnd, top_hwnd]):
            if h:
                style = user32.GetWindowLongW(h, GWL_EXSTYLE)
                if enable:
                    user32.SetWindowLongW(h, GWL_EXSTYLE, style | WS_EX_LAYERED | WS_EX_TRANSPARENT)
                else:
                    user32.SetWindowLongW(h, GWL_EXSTYLE, (style | WS_EX_LAYERED) & ~WS_EX_TRANSPARENT)
    except Exception:
        pass


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
            user32.RegisterHotKey(None, self.HOTKEY_ID_F8, 0, VK_F8)

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

