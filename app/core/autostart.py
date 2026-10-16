"""
Windows Autostart Manager (Registry Run + Startup folder)

Lệnh Run luôn lấy theo chỗ app ĐANG CHẠY / ĐANG CÀI — không hardcode ổ đĩa hay path cũ.
- Bản đóng gói (FloatingClock.exe): ghi đúng sys.executable hiện tại.
- Dev/portable: ưu tiên FloatingClock.exe cạnh thư mục app, mới fallback pythonw + main.py.
"""
import os
import re
import sys
import winreg
from app.config import APP_DIR

REG_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "FloatingClock"
# Trùng tên shortcut Inno Setup cũ: {userstartup}\{#MyAppName}.lnk
STARTUP_SHORTCUT_NAMES = (
    "Floating Clock.lnk",
    "FloatingClock.lnk",
    "Top Floating Clock.lnk",
)


def _startup_folder():
    appdata = os.environ.get("APPDATA") or ""
    return os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs\Startup")


def _startup_shortcut_paths():
    folder = _startup_folder()
    return [os.path.join(folder, name) for name in STARTUP_SHORTCUT_NAMES]


def _extract_paths_from_command(cmd):
    """Lấy các đường dẫn trong dấu ngoặc kép (hoặc token có \\) từ chuỗi lệnh Run."""
    if not cmd:
        return []
    paths = re.findall(r'"([^"]+)"', cmd)
    if paths:
        return paths
    token = cmd.strip().split(" ", 1)[0].strip('"')
    return [token] if token else []


def _command_targets_exist(cmd):
    """True nếu mọi path trong lệnh Run vẫn còn trên đĩa."""
    paths = _extract_paths_from_command(cmd)
    if not paths:
        return False
    return all(os.path.exists(p) for p in paths)


def _norm_path(path):
    return os.path.normcase(os.path.abspath(path))


def _find_bundled_exe():
    """Tìm FloatingClock.exe theo thư mục app hiện tại (portable / vừa build)."""
    candidates = (
        os.path.join(APP_DIR, "FloatingClock.exe"),
        os.path.join(APP_DIR, "dist", "FloatingClock.exe"),
    )
    for path in candidates:
        if os.path.isfile(path):
            return os.path.abspath(path)
    return None


def get_startup_command():
    """
    Command line autostart theo vị trí cài/chạy hiện tại (luôn abs path, không hardcode).

    Ưu tiên:
    1. Đang chạy exe đóng gói → chính file đó
    2. Có FloatingClock.exe trong APP_DIR / dist → dùng exe đó
    3. Dev: pythonw + main.py trong APP_DIR hiện tại
    """
    if getattr(sys, "frozen", False):
        return f'"{os.path.abspath(sys.executable)}"'

    bundled = _find_bundled_exe()
    if bundled:
        return f'"{bundled}"'

    main_script = os.path.join(APP_DIR, "main.py")
    if not os.path.isfile(main_script):
        main_script = os.path.join(APP_DIR, "floating_clock.py")
    main_script = os.path.abspath(main_script)

    py_dir = os.path.dirname(os.path.abspath(sys.executable))
    pythonw = os.path.join(py_dir, "pythonw.exe")
    if os.path.isfile(pythonw) and os.path.isfile(main_script):
        return f'"{pythonw}" "{main_script}"'

    bat_path = os.path.join(APP_DIR, "run_clock.bat")
    if os.path.isfile(bat_path):
        return f'"{os.path.abspath(bat_path)}"'

    if os.path.isfile(main_script):
        return f'"{os.path.abspath(sys.executable)}" "{main_script}"'

    return f'"{os.path.abspath(sys.executable)}"'


def _read_run_value():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY_PATH, 0, winreg.KEY_READ) as key:
            val, _ = winreg.QueryValueEx(key, APP_NAME)
            return val if isinstance(val, str) else None
    except OSError:
        return None


def _write_run_value(cmd):
    with winreg.CreateKeyEx(
        winreg.HKEY_CURRENT_USER,
        REG_KEY_PATH,
        0,
        winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE,
    ) as key:
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)


def _delete_run_value():
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            REG_KEY_PATH,
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
        return True
    except OSError:
        return False


def _has_startup_shortcut():
    return any(os.path.exists(p) for p in _startup_shortcut_paths())


def _remove_startup_shortcuts():
    removed = False
    for path in _startup_shortcut_paths():
        try:
            if os.path.exists(path):
                os.remove(path)
                removed = True
        except OSError:
            pass
    return removed


def is_start_with_windows():
    """
    True chỉ khi có cơ chế autostart CÒN HỢP LỆ:
    - Registry Run trỏ tới file còn tồn tại, hoặc
    - Shortcut trong thư mục Startup (từ installer cũ) còn tồn tại.
    """
    val = _read_run_value()
    if val and _command_targets_exist(val):
        return True
    if _has_startup_shortcut():
        return True
    return False


def repair_autostart_if_needed():
    """
    Đồng bộ Run key theo chỗ install/chạy hiện tại:
    - Path trong registry đã chết → ghi lại lệnh của bản đang mở
    - Đang chạy .exe đóng gói mà registry trỏ exe khác (đổi thư mục cài) → cập nhật
    Không tạo mới nếu user chưa từng bật autostart.
    """
    try:
        val = _read_run_value()
        if val is None:
            return False

        preferred = get_startup_command()
        if not _command_targets_exist(preferred):
            return False

        need_update = False
        if not _command_targets_exist(val):
            need_update = True
        elif getattr(sys, "frozen", False):
            paths = _extract_paths_from_command(val)
            reg_target = _norm_path(paths[0]) if paths else ""
            current_exe = _norm_path(sys.executable)
            if reg_target != current_exe:
                need_update = True

        if need_update:
            _write_run_value(preferred)
            _remove_startup_shortcuts()
            return True
    except Exception:
        pass
    return False


def set_start_with_windows(enable=True):
    """
    Bật/tắt tự khởi động cùng Windows.
    Bật: luôn ghi path của bản đang chạy (theo chỗ install hiện tại).
    Tắt: xóa Registry + shortcut Startup cũ.
    """
    try:
        if enable:
            cmd = get_startup_command()
            if not _command_targets_exist(cmd):
                return False
            _write_run_value(cmd)
            _remove_startup_shortcuts()
            return True

        ok_reg = _delete_run_value()
        _remove_startup_shortcuts()
        return ok_reg or _read_run_value() is None
    except Exception:
        return False
