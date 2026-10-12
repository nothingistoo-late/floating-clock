"""
Update Notification Dialog
Displays release notes and provides direct link to download the new version.
"""
import tkinter as tk
from tkinter import ttk
import webbrowser

from app.constants import GITHUB_RELEASES_URL


class UpdateNotificationDialog(tk.Toplevel):
    """Cửa sổ thông báo có phiên bản mới với changelog và nút tải về"""

    def __init__(self, master, update_info):
        real_master = getattr(master, "root", master)
        super().__init__(real_master)
        self.withdraw()
        self.update_info = update_info or {}
        latest_ver = self.update_info.get("latest_version", "Mới nhất")
        curr_ver = self.update_info.get("current_version", "")
        self.title(f"🚀 Có bản cập nhật mới ({latest_ver})")
        self.attributes("-topmost", True)
        self.configure(bg="#0f172a")
        self.resizable(False, False)

        w, h = 480, 360
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        f = tk.Frame(self, bg="#0f172a", padx=18, pady=16)
        f.pack(fill="both", expand=True)

        # Header
        header_f = tk.Frame(f, bg="#0f172a")
        header_f.pack(fill="x", pady=(0, 10))

        tk.Label(
            header_f,
            text="🚀  ĐÃ CÓ PHIÊN BẢN MỚI!",
            font=("Segoe UI", 12, "bold"),
            bg="#0f172a",
            fg="#38BDF8",
        ).pack(anchor="w")

        sub_txt = f"Phiên bản đang dùng: {curr_ver}  ➜  Bản mới nhất: {latest_ver}"
        tk.Label(
            header_f,
            text=sub_txt,
            font=("Segoe UI", 9),
            bg="#0f172a",
            fg="#A78BFA",
        ).pack(anchor="w", pady=(2, 0))

        # Title of the release
        rel_title = self.update_info.get("title", "")
        if rel_title and rel_title != latest_ver:
            tk.Label(
                f,
                text=f"Tiêu đề: {rel_title}",
                font=("Segoe UI", 9, "bold"),
                bg="#0f172a",
                fg="#F8FAFC",
            ).pack(anchor="w", pady=(0, 6))

        # Changelog area
        tk.Label(
            f,
            text="📋 Những thay đổi mới (Changelog):",
            font=("Segoe UI", 8, "bold"),
            bg="#0f172a",
            fg="#94A3B8",
        ).pack(anchor="w", pady=(2, 4))

        box_f = tk.Frame(f, bg="#1e2430", highlightbackground="#334155", highlightthickness=1)
        box_f.pack(fill="both", expand=True, pady=(0, 14))

        scroll = tk.Scrollbar(box_f)
        scroll.pack(side="right", fill="y")

        txt_box = tk.Text(
            box_f,
            font=("Consolas", 9),
            bg="#1e2430",
            fg="#E2E8F0",
            wrap="word",
            padx=8,
            pady=8,
            relief="flat",
            yscrollcommand=scroll.set,
        )
        txt_box.pack(side="left", fill="both", expand=True)
        scroll.config(command=txt_box.yview)

        changelog_txt = self.update_info.get("changelog", "").strip() or "Bản cập nhật tối ưu hiệu năng và sửa các lỗi nhỏ (づ｡◕‿‿◕｡)づ."
        txt_box.insert("1.0", changelog_txt)
        txt_box.configure(state="disabled")

        # Buttons
        btn_f = tk.Frame(f, bg="#0f172a")
        btn_f.pack(fill="x")

        btn_dl = tk.Button(
            btn_f,
            text="⬇️ Tải bản mới ngay (GitHub)",
            font=("Segoe UI", 9, "bold"),
            bg="#059669",
            fg="#FFFFFF",
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self._open_download,
        )
        btn_dl.pack(side="right", padx=(8, 0))

        btn_close = tk.Button(
            btn_f,
            text="Để sau",
            font=("Segoe UI", 9),
            bg="#334155",
            fg="#F1F5F9",
            relief="flat",
            padx=12,
            pady=6,
            cursor="hand2",
            command=self.destroy,
        )
        btn_close.pack(side="right")

        self.deiconify()
        self.lift()
        self.focus_force()

    def _open_download(self):
        url = self.update_info.get("release_url") or GITHUB_RELEASES_URL
        try:
            webbrowser.open(url)
        except Exception:
            pass
        self.destroy()
