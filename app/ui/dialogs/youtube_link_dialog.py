"""
Dialog dán link YouTube để xem khi rê chuột vào đồng hồ
"""
import tkinter as tk

from app.services.youtube_player import parse_youtube_url


class YouTubeLinkDialog(tk.Toplevel):
    """Nhập / dán link YouTube → phát trong popup hover của đồng hồ."""

    def __init__(self, master_app, initial_url=""):
        super().__init__(master_app.root)
        self.withdraw()
        self.app = master_app
        self.title("📺 Xem YouTube khi rê chuột")
        self.attributes("-topmost", True)
        self.configure(bg="#11141c")
        self.resizable(False, False)

        w, h = 460, 250
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

        f = tk.Frame(self, bg="#11141c", padx=16, pady=14)
        f.pack(fill="both", expand=True)

        tk.Label(
            f, text="📺 XEM YOUTUBE KHI RÊ CHUỘT",
            font=("Segoe UI", 11, "bold"), bg="#11141c", fg="#F87171"
        ).pack(anchor="w", pady=(0, 4))

        note = (
            "Giữ chuột trên đồng hồ ~3 giây → hiện video & phát tiếp.\n"
            "Rê chuột ra ngoài → ẩn video & tạm dừng, đồng hồ hiện lại bình thường.\n"
            "Dán link playlist / Mix cũng được. Thanh dưới video: ⏮ ⏯ ⏭, tua, âm lượng, tốc độ, ⚙ chất lượng.\n"
            "Phát trực tuyến, không tải video về máy (￣▽￣)ノ"
        )
        tk.Label(
            f, text=note, font=("Segoe UI", 8), bg="#11141c", fg="#94A3B8",
            justify="left", wraplength=420
        ).pack(anchor="w", pady=(0, 10))

        self.ent_url = tk.Entry(
            f, font=("Consolas", 10), bg="#1e2430", fg="#F8FAFC",
            insertbackground="#fff", relief="flat"
        )
        self.ent_url.pack(fill="x", ipady=5)
        self.ent_url.insert(0, initial_url or self._clipboard_youtube_url() or "")
        self.ent_url.focus_set()
        self.ent_url.select_range(0, "end")

        self.lbl_err = tk.Label(
            f, text="", font=("Segoe UI", 8), bg="#11141c", fg="#F87171",
            justify="left", wraplength=420
        )
        self.lbl_err.pack(anchor="w", pady=(4, 0))

        btn_box = tk.Frame(f, bg="#11141c")
        btn_box.pack(fill="x", pady=(8, 0))
        tk.Button(
            btn_box, text="▶ Phát", font=("Segoe UI", 9, "bold"),
            bg="#DC2626", fg="#FFFFFF", relief="flat", padx=16, pady=6,
            cursor="hand2", command=self._confirm
        ).pack(side="left", padx=(0, 8))
        tk.Button(
            btn_box, text="Hủy", font=("Segoe UI", 9),
            bg="#334155", fg="#FFFFFF", relief="flat", padx=12, pady=6,
            cursor="hand2", command=self.destroy
        ).pack(side="left")

        self.bind("<Return>", lambda e: self._confirm())
        self.bind("<Escape>", lambda e: self.destroy())
        self.deiconify()
        self.lift()
        self.focus_force()

    def _clipboard_youtube_url(self):
        """Clipboard đang chứa link YouTube thì điền sẵn luôn cho tiện."""
        try:
            txt = self.clipboard_get()
        except Exception:
            return ""
        return txt.strip() if parse_youtube_url(txt) else ""

    def _confirm(self):
        raw = self.ent_url.get().strip()
        if not parse_youtube_url(raw):
            self.lbl_err.configure(text="Link không hợp lệ — dán link dạng youtube.com/watch?v=... hoặc youtu.be/...")
            return
        # Đóng dialog trước để popup video không bị dialog che / tranh focus
        self.destroy()
        self.app.play_youtube_url(raw)
