"""
Dialog thống kê chi tiết tiền lương (gross / OT / BHXH / net)
"""
import tkinter as tk
from tkinter import messagebox
from datetime import datetime

from app.core.salary_calculator import (
    calculate_salary_info,
    clear_ot_session,
    set_ot_start,
)


def _vnd(n):
    return f"{int(n):,} đ".replace(",", ".")


class SalaryStatsDialog(tk.Toplevel):
    def __init__(self, master_app):
        super().__init__(master_app.root)
        self.withdraw()
        self.app = master_app
        self.title("💸 Thống kê tiền lương")
        self.attributes("-topmost", True)
        self.configure(bg="#11141c")
        self.resizable(False, False)

        w, h = 460, 520
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

        self._poll_id = None

        f = tk.Frame(self, bg="#11141c", padx=16, pady=12)
        f.pack(fill="both", expand=True)

        tk.Label(
            f, text="💸 THỐNG KÊ TIỀN LƯƠNG CHI TIẾT",
            font=("Segoe UI", 11, "bold"), bg="#11141c", fg="#10B981"
        ).pack(anchor="w", pady=(0, 6))

        self.body = tk.Label(
            f, text="", font=("Consolas", 9), bg="#11141c", fg="#E2E8F0",
            justify="left", anchor="nw"
        )
        self.body.pack(fill="both", expand=True, pady=(0, 8))

        # Sửa giờ OT nhanh
        ot_f = tk.LabelFrame(
            f, text="⏱ Tăng ca hôm nay", font=("Segoe UI", 9, "bold"),
            bg="#11141c", fg="#FBBF24", padx=8, pady=6
        )
        ot_f.pack(fill="x", pady=(0, 8))

        row = tk.Frame(ot_f, bg="#11141c")
        row.pack(fill="x")
        tk.Label(row, text="Giờ bắt đầu:", font=("Segoe UI", 8),
                 bg="#11141c", fg="#F8FAFC").pack(side="left")
        self.ent_ot = tk.Entry(
            row, font=("Consolas", 10), width=8, bg="#1e2430", fg="#FBBF24",
            insertbackground="#fff", relief="flat", justify="center"
        )
        self.ent_ot.pack(side="left", padx=6, ipady=2)

        tk.Button(
            row, text="Áp dụng", font=("Segoe UI", 8, "bold"),
            bg="#D97706", fg="#fff", relief="flat", padx=8, pady=2,
            cursor="hand2", command=self._apply_ot
        ).pack(side="left", padx=4)

        tk.Button(
            row, text="Dừng OT", font=("Segoe UI", 8),
            bg="#334155", fg="#fff", relief="flat", padx=8, pady=2,
            cursor="hand2", command=self._stop_ot
        ).pack(side="left")

        tk.Button(
            f, text="Đóng", font=("Segoe UI", 9),
            bg="#334155", fg="#fff", relief="flat", padx=14, pady=5,
            cursor="hand2", command=self.destroy
        ).pack(anchor="e")

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.refresh()
        self.deiconify()
        self.lift()
        self._schedule_poll()

    def _schedule_poll(self):
        try:
            if self.winfo_exists():
                self.refresh()
                self._poll_id = self.after(1000, self._schedule_poll)
        except Exception:
            pass

    def _on_close(self):
        if self._poll_id:
            try:
                self.after_cancel(self._poll_id)
            except Exception:
                pass
        self.destroy()

    def refresh(self):
        now = datetime.now()
        info = calculate_salary_info(now, self.app.config, self.app.get_today_departure_info)
        if not info:
            self.body.configure(text="Bật đếm lương trong Cài đặt để xem thống kê. (´・ω・`)")
            return

        sal = self.app.config.get("salary", {})
        disp = info.get("clock_display", "gross")
        lines = [
            f"Lương tháng: {_vnd(info.get('monthly', 0))}",
            f"Đơn giá ngày: {_vnd(info.get('daily_rate', 0))}  •  Giờ: {_vnd(info.get('hourly_rate', 0))}/h",
            f"Chu kỳ: {info.get('cycle_label', '')}  •  Ngày làm đã qua: {info.get('past_work_days', 0)}",
            f"Đồng hồ đang hiện: {disp.upper()}",
            "",
            "── Hôm nay ──",
            f"Giờ làm ca: {info.get('worked_hours', 0):.2f}h / {info.get('today_scheduled_hours', 0):g}h",
            f"Lương ca:   {_vnd(info.get('daily_earned', 0))}",
        ]

        if info.get("ot_active"):
            lines.append(
                f"OT từ {info.get('ot_start_display', '?')} → now: "
                f"{info.get('ot_hours', 0):.2f}h ×{info.get('ot_multiplier_used', 1):g} "
                f"({info.get('ot_kind', '')})"
            )
            lines.append(f"Tiền OT:    {_vnd(info.get('ot_earned', 0))}")
            if not self.ent_ot.get().strip():
                self.ent_ot.delete(0, "end")
                self.ent_ot.insert(0, info.get("ot_start_display", ""))
        else:
            lines.append("OT: chưa bắt đầu")
            if not self.ent_ot.get().strip() and info.get("dt_end_display"):
                self.ent_ot.delete(0, "end")
                self.ent_ot.insert(0, info.get("dt_end_display", ""))

        lines.extend([
            f"GROSS ngày: {_vnd(info.get('daily_gross', 0))}",
            f"BHXH ngày:  {_vnd(info.get('bhxh_daily', 0))}" if info.get("deduct_bhxh") else "BHXH: tắt",
            f"NET ngày:   {_vnd(info.get('daily_net', 0))}",
            "",
            f"── {info.get('cycle_label', 'Tháng')} ──",
            f"GROSS: {_vnd(info.get('month_gross', 0))}",
        ])
        if info.get("deduct_bhxh"):
            lines.append(
                f"BHXH ước: {_vnd(info.get('bhxh_month', 0))} "
                f"(full tháng ~{_vnd(info.get('bhxh_month_full', 0))} "
                f"@ {info.get('bhxh_rate_pct', 10.5):g}% × {_vnd(info.get('bhxh_base', 0))})"
            )
        lines.append(f"NET:   {_vnd(info.get('month_net', 0))}")

        self.body.configure(text="\n".join(lines))

    def _apply_ot(self):
        raw = self.ent_ot.get().strip()
        try:
            set_ot_start(self.app.config, raw, datetime.now())
            self.app.save_config()
            self.refresh()
            if hasattr(self.app, "update_extra_info_visibility"):
                self.app.update_extra_info_visibility()
        except Exception as e:
            messagebox.showerror("Lỗi", str(e), parent=self)

    def _stop_ot(self):
        clear_ot_session(self.app.config)
        self.app.save_config()
        self.ent_ot.delete(0, "end")
        self.refresh()
        if hasattr(self.app, "update_extra_info_visibility"):
            self.app.update_extra_info_visibility()
