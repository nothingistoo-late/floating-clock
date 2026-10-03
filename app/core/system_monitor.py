"""
Win32 System Monitor (RAM and CPU usage without third-party dependencies)
"""
import ctypes


class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


def get_ram_usage_percent():
    """Lấy % dung lượng RAM đang sử dụng qua Windows GlobalMemoryStatusEx API"""
    try:
        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
            return int(stat.dwMemoryLoad)
    except Exception:
        pass
    return 0


_prev_idle = 0
_prev_kernel = 0
_prev_user = 0


def get_cpu_usage_percent():
    """Lấy % tải CPU hệ thống qua Windows GetSystemTimes API"""
    global _prev_idle, _prev_kernel, _prev_user
    try:
        idle = ctypes.c_ulonglong()
        kernel = ctypes.c_ulonglong()
        user = ctypes.c_ulonglong()
        if ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)):
            i = idle.value
            k = kernel.value
            u = user.value
            if _prev_kernel == 0:
                _prev_idle, _prev_kernel, _prev_user = i, k, u
                return 0
            d_idle = i - _prev_idle
            d_kernel = k - _prev_kernel
            d_user = u - _prev_user
            _prev_idle, _prev_kernel, _prev_user = i, k, u
            total = d_kernel + d_user
            if total > 0:
                pct = int((1.0 - (d_idle / total)) * 100)
                return max(0, min(100, pct))
    except Exception:
        pass
    return 0
