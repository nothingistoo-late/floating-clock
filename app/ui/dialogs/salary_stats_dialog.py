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

        w, h = 470, 560
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
        self.body.pack(fill="both", expand=True, pady=(0, 6))

        # Tùy chọn khấu trừ BHXH & chế độ hiển thị đồng hồ
        sal = self.app.config.get("salary", {})
        cfg_f = tk.LabelFrame(
            f, text="⚙️ Thiết lập hiển thị & Khấu trừ NET", font=("Segoe UI", 9, "bold"),
            bg="#11141c", fg="#38BDF8", padx=8, pady=6
        )
        cfg_f.pack(fill="x", pady=(0, 6))

        self.var_deduct_bhxh = tk.BooleanVar(value=sal.get("deduct_bhxh", True))
        self.cb_bhxh = tk.Checkbutton(
            cfg_f, text=f"Trừ BHXH người lao động ({float(sal.get('bhxh_rate_pct', 10.5)):g}%) để tính NET",
            variable=self.var_deduct_bhxh, command=self._on_toggle_bhxh,
            font=("Segoe UI", 8, "bold"), bg="#11141c", fg="#38BDF8",
            selectcolor="#1e2430", activebackground="#11141c", cursor="hand2"
        )
        self.cb_bhxh.pack(anchor="w")

        disp_row = tk.Frame(cfg_f, bg="#11141c")
        disp_row.pack(fill="x", pady=(3, 0))
        tk.Label(disp_row, text="Đồng hồ hiện:", font=("Segoe UI", 8), bg="#11141c", fg="#94A3B8").pack(side="left")
        self.var_clock_disp = tk.StringVar(value=sal.get("clock_display", "gross"))
        tk.Radiobutton(
            disp_row, text="GROSS", variable=self.var_clock_disp, value="gross",
            command=self._on_change_clock_disp, font=("Segoe UI", 8, "bold"),
            bg="#11141c", fg="#34D399", selectcolor="#1e2430", activebackground="#11141c", cursor="hand2"
        ).pack(side="left", padx=(8, 10))
        tk.Radiobutton(
            disp_row, text="NET (sau trừ)", variable=self.var_clock_disp, value="net",
            command=self._on_change_clock_disp, font=("Segoe UI", 8, "bold"),
            bg="#11141c", fg="#38BDF8", selectcolor="#1e2430", activebackground="#11141c", cursor="hand2"
        ).pack(side="left")

        # Sửa giờ OT nhanh
        ot_f = tk.LabelFrame(
            f, text="⏱ Tăng ca hôm nay", font=("Segoe UI", 9, "bold"),
            bg="#11141c", fg="#FBBF24", padx=8, pady=6
        )
        ot_f.pack(fill="x", pady=(0, 6))

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

        bottom_row = tk.Frame(f, bg="#11141c")
        bottom_row.pack(fill="x", pady=(4, 0))

        tk.Label(
            bottom_row, text="💡 Tip: Double-click dòng lương để mở bảng này",
            font=("Segoe UI", 8, "italic"), bg="#11141c", fg="#64748B"
        ).pack(side="left")

        tk.Button(
            bottom_row, text="Đóng", font=("Segoe UI", 9),
            bg="#334155", fg="#fff", relief="flat", padx=14, pady=4,
            cursor="hand2", command=self.destroy
        ).pack(side="right")

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

    def _on_toggle_bhxh(self):
        self.app.config.setdefault("salary", {})
        self.app.config["salary"]["deduct_bhxh"] = self.var_deduct_bhxh.get()
        self.app.save_config()
        self.refresh()
        if hasattr(self.app, "update_extra_info_visibility"):
            self.app.update_extra_info_visibility()

    def _on_change_clock_disp(self):
        self.app.config.setdefault("salary", {})
        self.app.config["salary"]["clock_display"] = self.var_clock_disp.get()
        self.app.save_config()
        self.refresh()
        if hasattr(self.app, "update_extra_info_visibility"):
            self.app.update_extra_info_visibility()

    def refresh(self):
        now = datetime.now()
        info = calculate_salary_info(now, self.app.config, self.app.get_today_departure_info)
        if not info:
            self.body.configure(text="Bật đếm lương trong Cài đặt để xem thống kê. (´・ω・`)")
            return

        sal = self.app.config.get("salary", {})
        # Đồng bộ trạng thái giao diện nếu có thay đổi từ cấu hình ngoài
        cur_deduct = bool(sal.get("deduct_bhxh", True))
        if self.var_deduct_bhxh.get() != cur_deduct:
            self.var_deduct_bhxh.set(cur_deduct)
        cur_disp = sal.get("clock_display", "gross")
        if self.var_clock_disp.get() != cur_disp:
            self.var_clock_disp.set(cur_disp)

        disp = info.get("clock_display", "gross")
        lines = [
            f"Lương tháng:  {_vnd(info.get('monthly', 0))}",
            f"Đơn giá ngày: {_vnd(info.get('daily_rate', 0))}  •  Giờ: {_vnd(info.get('hourly_rate', 0))}/h",
            f"Chu kỳ:       {info.get('cycle_label', '')}  •  Ngày làm đã qua: {info.get('past_work_days', 0)}",
            f"Đồng hồ hiện: {disp.upper()}",
            "",
            "── Hôm nay ──",
            f"Giờ làm ca:   {info.get('worked_hours', 0):.2f}h / {info.get('today_scheduled_hours', 0):g}h",
            f"Lương ca:     {_vnd(info.get('daily_earned', 0))}",
        ]

        if info.get("ot_active"):
            lines.append(
                f"OT từ {info.get('ot_start_display', '?')} → now: "
                f"{info.get('ot_hours', 0):.2f}h ×{info.get('ot_multiplier_used', 1):g} "
                f"({info.get('ot_kind', '')})"
            )
            lines.append(f"Tiền OT:      {_vnd(info.get('ot_earned', 0))}")
            if not self.ent_ot.get().strip():
                self.ent_ot.delete(0, "end")
                self.ent_ot.insert(0, info.get("ot_start_display", ""))
        else:
            lines.append("OT:           chưa bắt đầu")
            if not self.ent_ot.get().strip():
                # Ngày nghỉ / lễ: gợi ý giờ hiện tại; ngày làm: gợi ý giờ tan ca
                if info.get("is_weekend") or info.get("is_holiday"):
                    suggest = now.strftime("%H:%M")
                else:
                    suggest = info.get("dt_end_display", "")
                if suggest:
                    self.ent_ot.delete(0, "end")
                    self.ent_ot.insert(0, suggest)

        lines.append(f"GROSS ngày:   {_vnd(info.get('daily_gross', 0))}")
        if info.get("deduct_bhxh"):
            lines.append(f"Trừ BHXH:    -{_vnd(info.get('bhxh_daily', 0))} ({info.get('bhxh_rate_pct', 10.5):g}%)")
        else:
            lines.append("Trừ BHXH:     Tắt (chưa trừ)")

        lines.extend([
            f"NET ngày:     {_vnd(info.get('daily_net', 0))}",
            "",
            f"── {info.get('cycle_label', 'Tháng')} ──",
            f"GROSS:        {_vnd(info.get('month_gross', 0))}",
        ])

        if info.get("deduct_bhxh"):
            lines.append(
                f"Trừ BHXH:    -{_vnd(info.get('bhxh_month', 0))} "
                f"(ước tính kỳ • full ~{_vnd(info.get('bhxh_month_full', 0))})"
            )
        else:
            lines.append("Trừ BHXH:     Tắt (chưa trừ)")

        lines.append(f"NET:          {_vnd(info.get('month_net', 0))}")

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
