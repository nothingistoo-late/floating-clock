"""
Error logger dùng chung — ghi lỗi ra floating_clock_error.log cạnh ứng dụng.
Tách riêng khỏi app/main.py để các module UI import được mà không bị vòng import.
"""
import datetime
import os
import time
import traceback

from app.config import APP_DIR

LOG_FILE = os.path.join(APP_DIR, "floating_clock_error.log")

# Chống spam log: cùng một lỗi lặp lại liên tục (vd: trong vòng lặp 50ms) chỉ ghi 1 lần / khoảng thời gian
_last_logged = {}


def log_error(err_msg, source="General"):
    """Ghi một bản tin lỗi kèm thời gian và nguồn phát sinh."""
    try:
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{now_str}] [{source}]\n{err_msg}\n{'-'*60}\n")
    except Exception:
        pass


def log_exception_throttled(source="General", min_interval_sec=60.0):
    """
    Ghi traceback của exception đang xử lý, nhưng cùng (source + nội dung lỗi)
    chỉ ghi tối đa 1 lần mỗi min_interval_sec giây.
    Gọi bên trong khối `except`.
    """
    try:
        err_msg = traceback.format_exc()
        key = (source, err_msg)
        now_ts = time.time()
        if now_ts - _last_logged.get(key, 0.0) < min_interval_sec:
            return
        _last_logged[key] = now_ts
        # Giữ dict nhỏ gọn
        if len(_last_logged) > 200:
            _last_logged.clear()
        log_error(err_msg, source=source)
    except Exception:
        pass
