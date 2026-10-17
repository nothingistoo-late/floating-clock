"""
Dialog nhập giờ bắt đầu tăng ca
"""
import tkinter as tk
from tkinter import messagebox
from datetime import datetime

from app.core.salary_calculator import resolve_ot_multiplier, set_ot_start


class OvertimeStartDialog(tk.Toplevel):
    """Nhập giờ bắt đầu OT — tiền OT = (now - start) × đơn giá giờ × hệ số."""

    def __init__(self, master_app, default_time="17:45"):
        super().__init__(master_app.root)
        self.withdraw()
        self.app = master_app
        self.title("⏱ Bắt đầu tăng ca")
        self.attributes("-topmost", True)
        self.configure(bg="#11141c")
        self.resizable(False, False)

        w, h = 420, 260
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

        now = datetime.now()
        mult, kind = resolve_ot_multiplier(now, self.app.config)

        f = tk.Frame(self, bg="#11141c", padx=16, pady=14)
        f.pack(fill="both", expand=True)

        tk.Label(
            f, text="⏱ BẮT ĐẦU TĂNG CA",
            font=("Segoe UI", 11, "bold"), bg="#11141c", fg="#FBBF24"
        ).pack(anchor="w", pady=(0, 4))

        note = (
            "Tiền OT = từ giờ bắt đầu đến hiện tại × đơn giá giờ × hệ số.\n"
            f"Hệ số hôm nay: ×{mult:g} ({kind})"
        )
        tk.Label(
            f, text=note, font=("Segoe UI", 8), bg="#11141c", fg="#94A3B8",
            justify="left", wraplength=380
        ).pack(anchor="w", pady=(0, 10))

        row = tk.Frame(f, bg="#11141c")
        row.pack(fill="x", pady=(0, 8))
        tk.Label(row, text="Giờ bắt đầu (HH:MM):", font=("Segoe UI", 9, "bold"),
                 bg="#11141c", fg="#F8FAFC").pack(side="left")
        self.ent_time = tk.Entry(
            row, font=("Consolas", 11), width=8, bg="#1e2430", fg="#FBBF24",
            insertbackground="#fff", relief="flat", justify="center"
        )
        self.ent_time.pack(side="left", padx=10, ipady=3)
        self.ent_time.insert(0, (default_time or now.strftime("%H:%M"))[:5])
        self.ent_time.focus_set()
        self.ent_time.select_range(0, "end")

        btn_box = tk.Frame(f, bg="#11141c")
        btn_box.pack(fill="x", pady=(12, 0))

        tk.Button(
            btn_box, text="▶ Bắt đầu đếm OT",
            font=("Segoe UI", 9, "bold"), bg="#D97706", fg="#FFFFFF",
            relief="flat", padx=14, pady=6, cursor="hand2",
            command=self._confirm
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            btn_box, text="Hủy",
            font=("Segoe UI", 9), bg="#334155", fg="#FFFFFF",
            relief="flat", padx=12, pady=6, cursor="hand2",
            command=self.destroy
        ).pack(side="left")

        self.bind("<Return>", lambda e: self._confirm())
        self.bind("<Escape>", lambda e: self.destroy())
        self.deiconify()
        self.lift()
        self.focus_force()

    def _confirm(self):
        raw = self.ent_time.get().strip()
        try:
            set_ot_start(self.app.config, raw, datetime.now())
            self.app.save_config()
            if hasattr(self.app, "update_extra_info_visibility"):
                self.app.update_extra_info_visibility()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Lỗi", str(e), parent=self)
