"""
Main application runner
"""
import os
import sys
import tkinter as tk
from tkinter import messagebox
import traceback

# Prevent crashes in pythonw / noconsole when stdout/stderr are None
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

from app.ui.main_window import FloatingClock


def main():
    try:
        root = tk.Tk()
        root.withdraw()
        root.title("Top Floating Multi-Clock")
        app = FloatingClock(root)
        root.deiconify()
        root.mainloop()
    except Exception as e:
        err_msg = traceback.format_exc()
        try:
            messagebox.showerror("Floating Clock Error", f"Lỗi khởi động:\n\n{err_msg}")
        except Exception:
            print(f"Error: {err_msg}", file=sys.stderr)


if __name__ == "__main__":
    main()
