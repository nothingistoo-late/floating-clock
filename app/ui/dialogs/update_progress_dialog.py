"""
Cửa sổ nhỏ "Đang kiểm tra cập nhật..." — cho người dùng biết app đang làm gì trong lúc chờ
(kiểm tra bản app mới trên GitHub + cập nhật yt-dlp có thể mất vài chục giây).
"""
import tkinter as tk
from tkinter import ttk

BG = "#0f172a"


class UpdateProgressDialog(tk.Toplevel):
    """Hiện trạng thái từng phần, có thanh chạy. Bấm "Ẩn" thì vẫn kiểm tra ngầm và báo kết quả khi xong."""

    def __init__(self, master_app):
        super().__init__(master_app.root)
        self.withdraw()
        self.app = master_app
        self.title("🔄 Kiểm tra cập nhật")
        self.attributes("-topmost", True)
        self.configure(bg=BG)
        self.resizable(False, False)

        w, h = 400, 170
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

        f = tk.Frame(self, bg=BG, padx=16, pady=14)
        f.pack(fill="both", expand=True)

        tk.Label(
            f, text="🔄 Đang kiểm tra cập nhật...",
            font=("Segoe UI", 11, "bold"), bg=BG, fg="#38BDF8"
        ).pack(anchor="w")

        style = ttk.Style(self)
        try:
            style.configure("FC.Horizontal.TProgressbar", troughcolor="#1e293b",
                            background="#38BDF8", bordercolor=BG, lightcolor="#38BDF8", darkcolor="#38BDF8")
            bar_style = "FC.Horizontal.TProgressbar"
        except Exception:
            bar_style = "Horizontal.TProgressbar"
        self.bar = ttk.Progressbar(f, mode="indeterminate", length=360, style=bar_style)
        self.bar.pack(fill="x", pady=(8, 10))
        self.bar.start(12)

        row_style = dict(font=("Segoe UI", 9), bg=BG, fg="#E2E8F0", anchor="w", justify="left", wraplength=360)
        self.lbl_app = tk.Label(f, text="⏳ Ứng dụng: đang hỏi GitHub phiên bản mới nhất...", **row_style)
        self.lbl_app.pack(fill="x")
        self.lbl_ytdlp = tk.Label(f, text="⏳ yt-dlp (trình lấy video YouTube): đang chuẩn bị...", **row_style)
        self.lbl_ytdlp.pack(fill="x", pady=(2, 0))

        tk.Button(
            f, text="Ẩn (vẫn kiểm tra ngầm)", font=("Segoe UI", 8),
            bg="#334155", fg="#F1F5F9", relief="flat", padx=10, pady=3,
            cursor="hand2", command=self.close
        ).pack(anchor="e", pady=(10, 0))

        self.protocol("WM_DELETE_WINDOW", self.close)
        self.deiconify()
        self.lift()

    # ---------------- Cập nhật trạng thái ----------------
    def set_app_status(self, text, done=False):
        self._set(self.lbl_app, text, done)

    def set_ytdlp_status(self, text, done=False):
        self._set(self.lbl_ytdlp, text, done)

    def _set(self, label, text, done):
        try:
            if label.winfo_exists():
                label.configure(text=("✅ " if done else "⏳ ") + text)
        except Exception:
            pass

    def close(self):
        try:
            self.bar.stop()
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass
