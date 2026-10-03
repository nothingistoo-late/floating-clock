"""
Windows Registry Startup Manager (Autostart with Windows)
"""
import os
import sys
import winreg
from app.config import APP_DIR

REG_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "FloatingClock"


def get_startup_command():
    """Tạo command line phù hợp nhất để Windows khởi động ngầm không hiện terminal đen"""
    if getattr(sys, 'frozen', False):
        return f'"{sys.executable}"'

    # Check for run_clock.bat first
    bat_path = os.path.join(APP_DIR, "run_clock.bat")
    main_script = os.path.join(APP_DIR, "floating_clock.py")

    # Locate pythonw.exe
    py_dir = os.path.dirname(sys.executable)
    pythonw = os.path.join(py_dir, "pythonw.exe")
    if os.path.exists(pythonw):
        return f'"{pythonw}" "{main_script}"'

    if os.path.exists(bat_path):
        return f'"{bat_path}"'

    return f'"{sys.executable}" "{main_script}"'


def set_start_with_windows(enable=True):
    """Bật/tắt tự động khởi động cùng Windows qua Registry HKCU"""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY_PATH, 0, winreg.KEY_SET_VALUE)
        if enable:
            cmd = get_startup_command()
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def is_start_with_windows():
    """Kiểm tra ứng dụng có đang được đăng ký khởi động cùng Windows không"""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY_PATH, 0, winreg.KEY_READ)
        val, _ = winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return bool(val)
    except Exception:
        return False
