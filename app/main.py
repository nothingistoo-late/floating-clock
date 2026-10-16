"""
Main application runner
"""
import datetime
import os
import sys
import threading
import tkinter as tk
from tkinter import messagebox
import traceback

from app.config import APP_DIR

LOG_FILE = os.path.join(APP_DIR, "floating_clock_error.log")


def log_error(err_msg, source="General"):
    try:
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{now_str}] [{source}]\n{err_msg}\n{'-'*60}\n")
    except Exception:
        pass


def handle_uncaught_exception(exc_type, exc_val, exc_tb):
    err_msg = "".join(traceback.format_exception(exc_type, exc_val, exc_tb))
    log_error(err_msg, source="SysExceptHook")


def handle_thread_exception(args):
    err_msg = "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback))
    thread_name = getattr(args.thread, "name", "Thread")
    log_error(err_msg, source=f"Thread:{thread_name}")


sys.excepthook = handle_uncaught_exception
if hasattr(threading, "excepthook"):
    threading.excepthook = handle_thread_exception

# Prevent crashes in pythonw / noconsole when stdout/stderr are None or CP1252
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
else:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")
else:
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from app.core.autostart import repair_autostart_if_needed
from app.core.win32_utils import SingleInstanceMutex, activate_existing_floating_clock
from app.ui.main_window import FloatingClock


def main():
    # Luôn đảm bảo thư mục làm việc hiện tại (CWD) là thư mục gốc của ứng dụng
    try:
        os.chdir(APP_DIR)
    except Exception:
        pass

    # Kiểm tra chống chạy đè nhiều bản cùng lúc (Single Instance Lock)
    single_inst = SingleInstanceMutex()
    if single_inst.is_already_running():
        # Không thoát êm: kéo cửa sổ cũ lên (tránh trường hợp bản cũ bị ẩn/mờ nhìn như "mất")
        restored = False
        try:
            restored = activate_existing_floating_clock()
        except Exception:
            pass
        if not restored:
            try:
                messagebox.showinfo(
                    "Floating Clock",
                    "Floating Clock đang chạy rồi.\n"
                    "Nếu không thấy đồng hồ: mở Task Manager tắt pythonw/FloatingClock rồi mở lại.",
                )
            except Exception:
                pass
        return

    # Sửa registry autostart nếu còn entry nhưng path exe/script đã mất
    try:
        repair_autostart_if_needed()
    except Exception:
        pass

    try:
        root = tk.Tk()
        root.withdraw()
        root.title("Top Floating Multi-Clock")

        def _on_tk_exception(exc_type, exc_val, exc_tb):
            err_msg = "".join(traceback.format_exception(exc_type, exc_val, exc_tb))
            log_error(err_msg, source="TkCallback")

        root.report_callback_exception = _on_tk_exception

        app = FloatingClock(root)
        root.deiconify()
        root.mainloop()
    except Exception:
        err_msg = traceback.format_exc()
        log_error(err_msg, source="MainStartup")
        try:
            messagebox.showerror("Floating Clock Error", f"Lỗi khởi động:\n\n{err_msg}")
        except Exception:
            pass
    finally:
        single_inst.release()


if __name__ == "__main__":
    main()

