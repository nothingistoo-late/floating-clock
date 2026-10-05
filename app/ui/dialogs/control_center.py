"""
Control Center & Settings Dialog (All configuration tabs and tools)
"""
from datetime import datetime
import math
import tkinter as tk
from tkinter import colorchooser, messagebox, ttk
from app.constants import CITY_COORDINATES
from app.core.autostart import is_start_with_windows, set_start_with_windows
from app.services.sound_service import sound_mgr
from app.messages import HOLIDAYS_DATA
from app.core.salary_calculator import get_payday_countdown_info


class ControlCenterDialog(tk.Toplevel):
    def __init__(self, master_app, initial_tab=0):
        super().__init__(master_app.root)
        self.withdraw()
        self.app = master_app
        self.title("🎛️ Bảng Điều Khiển & Thiết Lập Hệ Thống")
        self.attributes("-topmost", True)
        self.configure(bg="#0f131a")
        self.resizable(False, False)

        w, h = 640, 520
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        self._create_ui(initial_tab)
        self.deiconify()

    def _create_ui(self, initial_tab=0):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TNotebook", background="#0f131a", borderwidth=0)
        style.configure("TNotebook.Tab", background="#1a202c", foreground="#94a3b8", font=("Segoe UI", 9, "bold"), padding=[10, 5])
        style.map("TNotebook.Tab", background=[("selected", "#2563eb")], foreground=[("selected", "#ffffff")])

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Tabs
        self.tab_target = tk.Frame(self.notebook, bg="#151a24", padx=16, pady=12)
        self.tab_salary = tk.Frame(self.notebook, bg="#151a24", padx=16, pady=12)
        self.tab_weather = tk.Frame(self.notebook, bg="#151a24", padx=16, pady=12)
        self.tab_focus_sound = tk.Frame(self.notebook, bg="#151a24", padx=16, pady=12)
        self.tab_milestones = tk.Frame(self.notebook, bg="#151a24", padx=16, pady=12)
        self.tab_timer = tk.Frame(self.notebook, bg="#151a24", padx=16, pady=12)
        self.tab_alarm = tk.Frame(self.notebook, bg="#151a24", padx=16, pady=12)
        self.tab_stopwatch = tk.Frame(self.notebook, bg="#151a24", padx=16, pady=12)
        self.tab_pomodoro = tk.Frame(self.notebook, bg="#151a24", padx=16, pady=12)
        self.tab_display = tk.Frame(self.notebook, bg="#151a24", padx=16, pady=12)

        self.notebook.add(self.tab_target, text="🎯 Giờ Tan Làm")
        self.notebook.add(self.tab_salary, text="💸 Tiền Lương")
        self.notebook.add(self.tab_weather, text="🌦️ Thời Tiết")
        self.notebook.add(self.tab_focus_sound, text="🎧 Âm Thanh")
        self.notebook.add(self.tab_milestones, text="📅 Ngày Lễ & Lương")
        self.notebook.add(self.tab_timer, text="⏳ Đếm Ngược")
        self.notebook.add(self.tab_alarm, text="⏰ Báo Thức")
        self.notebook.add(self.tab_stopwatch, text="⏱️ Bấm Giờ")
        self.notebook.add(self.tab_pomodoro, text="🍅 Pomodoro")
        self.notebook.add(self.tab_display, text="🎨 Giao Diện & AI")

        self._setup_target_tab()
        self._setup_salary_tab()
        self._setup_weather_tab()
        self._setup_focus_sound_tab()
        self._setup_milestones_tab()
        self._setup_timer_tab()
        self._setup_alarm_tab()
        self._setup_stopwatch_tab()
        self._setup_pomodoro_tab()
        self._setup_display_tab()

        try:
            self.notebook.select(initial_tab)
        except Exception:
            pass

        bottom_bar = tk.Frame(self, bg="#0f131a", padx=10, pady=6)
        bottom_bar.pack(fill="x", side="bottom")

        btn_close = tk.Button(
            bottom_bar,
            text="Đóng (Esc)",
            font=("Segoe UI", 9, "bold"),
            bg="#334155",
            fg="#FFFFFF",
            relief="flat",
            padx=14,
            pady=4,
            cursor="hand2",
            command=self.destroy
        )
        btn_close.pack(side="right")
        self.bind("<Escape>", lambda e: self.destroy())

    # ---------------- 🎯 TAB TARGET TIME ----------------
    def _setup_target_tab(self):
        f = self.tab_target
        work_cfg = self.app.config.get("work_departure", {})

        tk.Label(f, text="🏢 LỊCH TRÌNH TAN LÀM TỰ ĐỘNG THEO THỨ", font=("Segoe UI", 11, "bold"), bg="#151a24", fg="#38BDF8").pack(anchor="w", pady=(0, 4))
        tk.Label(f, text="Đồng hồ sẽ tự động nhận diện thứ trong tuần và đếm ngược chính xác.", font=("Segoe UI", 8), bg="#151a24", fg="#94A3B8").pack(anchor="w", pady=(0, 10))

        grid_f = tk.Frame(f, bg="#151a24")
        grid_f.pack(fill="x", pady=4)

        tk.Label(grid_f, text="Giờ bắt đầu làm:", font=("Segoe UI", 9), bg="#151a24", fg="#F8FAFC").grid(row=0, column=0, sticky="w", pady=4)
        self.ent_start_time = tk.Entry(grid_f, font=("Segoe UI", 9), width=10, bg="#1e2430", fg="#00FFCC", insertbackground="#fff", relief="flat")
        self.ent_start_time.insert(0, work_cfg.get("start_time", "08:30"))
        self.ent_start_time.grid(row=0, column=1, sticky="w", padx=10, pady=4)

        tk.Label(grid_f, text="Thứ 2 - Thứ 6 tan làm:", font=("Segoe UI", 9), bg="#151a24", fg="#F8FAFC").grid(row=1, column=0, sticky="w", pady=4)
        self.ent_mon_fri = tk.Entry(grid_f, font=("Segoe UI", 9), width=10, bg="#1e2430", fg="#00FFCC", insertbackground="#fff", relief="flat")
        self.ent_mon_fri.insert(0, work_cfg.get("mon_fri_time", "17:45"))
        self.ent_mon_fri.grid(row=1, column=1, sticky="w", padx=10, pady=4)

        tk.Label(grid_f, text="Thứ 7 tan làm sớm:", font=("Segoe UI", 9), bg="#151a24", fg="#F8FAFC").grid(row=2, column=0, sticky="w", pady=4)
        self.ent_sat = tk.Entry(grid_f, font=("Segoe UI", 9), width=10, bg="#1e2430", fg="#00FFCC", insertbackground="#fff", relief="flat")
        self.ent_sat.insert(0, work_cfg.get("sat_time", "16:00"))
        self.ent_sat.grid(row=2, column=1, sticky="w", padx=10, pady=4)

        tk.Label(grid_f, text="Nghỉ trưa (Bắt đầu):", font=("Segoe UI", 9), bg="#151a24", fg="#F8FAFC").grid(row=3, column=0, sticky="w", pady=4)
        self.ent_lunch_start = tk.Entry(grid_f, font=("Segoe UI", 9), width=10, bg="#1e2430", fg="#FCD34D", insertbackground="#fff", relief="flat")
        self.ent_lunch_start.insert(0, work_cfg.get("lunch_start", "12:00"))
        self.ent_lunch_start.grid(row=3, column=1, sticky="w", padx=10, pady=4)

        tk.Label(grid_f, text="Nghỉ trưa (Kết thúc):", font=("Segoe UI", 9), bg="#151a24", fg="#F8FAFC").grid(row=4, column=0, sticky="w", pady=4)
        self.ent_lunch_end = tk.Entry(grid_f, font=("Segoe UI", 9), width=10, bg="#1e2430", fg="#FCD34D", insertbackground="#fff", relief="flat")
        self.ent_lunch_end.insert(0, work_cfg.get("lunch_end", "13:15"))
        self.ent_lunch_end.grid(row=4, column=1, sticky="w", padx=10, pady=4)

        btn_save_work = tk.Button(
            f,
            text="💾 Lưu cấu hình giờ làm",
            font=("Segoe UI", 9, "bold"),
            bg="#2563EB",
            fg="#FFFFFF",
            relief="flat",
            padx=12,
            pady=5,
            cursor="hand2",
            command=self._save_work_schedule
        )
        btn_save_work.pack(anchor="w", pady=(8, 12))

        now = datetime.now()
        today_dep, today_tag = self.app.get_today_departure_info(now)
        self.btn_today_dep = tk.Button(
            f,
            text=f"🏢 ĐẾM NGƯỢC TAN LÀM HÔM NAY ({today_tag}: {today_dep[:5]})",
            font=("Segoe UI", 10, "bold"),
            bg="#059669",
            fg="#FFFFFF",
            relief="flat",
            padx=12,
            pady=8,
            cursor="hand2",
            command=self._start_today_departure
        )
        self.btn_today_dep.pack(fill="x", pady=(0, 14))

        tk.Label(f, text="🎯 ĐẶT MỐC GIỜ TÙY Ý", font=("Segoe UI", 10, "bold"), bg="#151a24", fg="#38BDF8").pack(anchor="w", pady=(6, 4))
        custom_box = tk.Frame(f, bg="#151a24")
        custom_box.pack(fill="x", pady=2)

        tk.Label(custom_box, text="Giờ:", font=("Segoe UI", 9), bg="#151a24", fg="#F8FAFC").pack(side="left")
        self.spin_tgt_h = tk.Spinbox(custom_box, from_=0, to=23, width=4, font=("Segoe UI", 9), bg="#1e2430", fg="#00FFCC")
        self.spin_tgt_h.delete(0, "end")
        self.spin_tgt_h.insert(0, "17")
        self.spin_tgt_h.pack(side="left", padx=4)

        tk.Label(custom_box, text="Phút:", font=("Segoe UI", 9), bg="#151a24", fg="#F8FAFC").pack(side="left")
        self.spin_tgt_m = tk.Spinbox(custom_box, from_=0, to=59, width=4, font=("Segoe UI", 9), bg="#1e2430", fg="#00FFCC")
        self.spin_tgt_m.delete(0, "end")
        self.spin_tgt_m.insert(0, "45")
        self.spin_tgt_m.pack(side="left", padx=4)

        tk.Label(custom_box, text="Nhãn:", font=("Segoe UI", 9), bg="#151a24", fg="#F8FAFC").pack(side="left", padx=(10, 4))
        self.ent_tgt_label = tk.Entry(custom_box, font=("Segoe UI", 9), width=12, bg="#1e2430", fg="#00FFCC", insertbackground="#fff", relief="flat")
        self.ent_tgt_label.insert(0, "Tan làm")
        self.ent_tgt_label.pack(side="left", padx=4)

        btn_apply_custom_tgt = tk.Button(
            custom_box,
            text="▶ Bắt đầu đếm",
            font=("Segoe UI", 8, "bold"),
            bg="#8B5CF6",
            fg="#FFFFFF",
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=self._apply_custom_target
        )
        btn_apply_custom_tgt.pack(side="right")

    def _save_work_schedule(self):
        try:
            st = self.ent_start_time.get().strip()
            mf = self.ent_mon_fri.get().strip()
            sa = self.ent_sat.get().strip()
            ls = self.ent_lunch_start.get().strip()
            le = self.ent_lunch_end.get().strip()
            for val, name in [(st, "Bắt đầu làm"), (mf, "T2-T6"), (sa, "Thứ 7"), (ls, "Nghỉ trưa bắt đầu"), (le, "Nghỉ trưa kết thúc")]:
                parts = val.split(":")
                if len(parts) != 2 or not (0 <= int(parts[0]) <= 23 and 0 <= int(parts[1]) <= 59):
                    raise ValueError(f"Giờ {name} không đúng định dạng HH:MM!")

            self.app.config.setdefault("work_departure", {})
            self.app.config["work_departure"]["start_time"] = st
            self.app.config["work_departure"]["mon_fri_time"] = mf
            self.app.config["work_departure"]["sat_time"] = sa
            self.app.config["work_departure"]["lunch_start"] = ls
            self.app.config["work_departure"]["lunch_end"] = le
            self.app.save_config()

            now = datetime.now()
            today_dep, today_tag = self.app.get_today_departure_info(now)
            self.btn_today_dep.configure(text=f"🏢 ĐẾM NGƯỢC TAN LÀM HÔM NAY ({today_tag}: {today_dep[:5]})")
            messagebox.showinfo("Thành công", "Đã lưu cấu hình giờ làm & nghỉ trưa thành công!", parent=self)
        except Exception as e:
            messagebox.showerror("Lỗi", str(e), parent=self)

    def _start_today_departure(self):
        now = datetime.now()
        today_dep, today_tag = self.app.get_today_departure_info(now)
        self.app.config["target_time_str"] = today_dep
        self.app.config["target_time_label"] = f"Tan làm ({today_tag})"
        self.app.config["target_time_active"] = True
        self.app.switch_mode("target_time")
        self.app.save_config()

    def _apply_custom_target(self):
        try:
            h = int(self.spin_tgt_h.get())
            m = int(self.spin_tgt_m.get())
            if not (0 <= h <= 23 and 0 <= m <= 59):
                raise ValueError()
            tgt_str = f"{h:02d}:{m:02d}:00"
            lbl = self.ent_tgt_label.get().strip() or "Mục tiêu"
            self.app.config["target_time_str"] = tgt_str
            self.app.config["target_time_label"] = lbl
            self.app.config["target_time_active"] = True
            self.app.switch_mode("target_time")
            self.app.save_config()
        except Exception:
            messagebox.showerror("Lỗi", "Giờ hoặc phút không hợp lệ!", parent=self)

    # ---------------- 💸 TAB SALARY ----------------
    def _setup_salary_tab(self):
        f = self.tab_salary
        sal_cfg = self.app.config.get("salary", {})
        work_cfg = self.app.config.get("work_departure", {})

        tk.Label(f, text="💸 THIẾT LẬP BỘ ĐẾM TIỀN LƯƠNG REALTIME", font=("Segoe UI", 11, "bold"), bg="#151a24", fg="#10B981").pack(anchor="w", pady=(0, 4))
        tk.Label(f, text="Đồng hồ tính toán số tiền tích lũy tăng từng giây trong giờ làm việc.", font=("Segoe UI", 8), bg="#151a24", fg="#94A3B8").pack(anchor="w", pady=(0, 8))

        grid_f = tk.Frame(f, bg="#151a24")
        grid_f.pack(fill="x", pady=2)

        tk.Label(grid_f, text="Mức lương tháng (VNĐ):", font=("Segoe UI", 9, "bold"), bg="#151a24", fg="#F8FAFC").grid(row=0, column=0, sticky="w", pady=4)
        self.ent_salary_monthly = tk.Entry(grid_f, font=("Segoe UI", 9), width=16, bg="#1e2430", fg="#34D399", insertbackground="#fff", relief="flat")
        self.ent_salary_monthly.insert(0, f"{int(sal_cfg.get('monthly', 15000000)):,}".replace(",", "."))
        self.ent_salary_monthly.grid(row=0, column=1, sticky="w", padx=10, pady=4)

        tk.Label(grid_f, text="Số ngày làm / tháng:", font=("Segoe UI", 9), bg="#151a24", fg="#F8FAFC").grid(row=1, column=0, sticky="w", pady=4)
        self.ent_sal_days = tk.Entry(grid_f, font=("Segoe UI", 9), width=16, bg="#1e2430", fg="#00FFCC", insertbackground="#fff", relief="flat")
        self.ent_sal_days.insert(0, str(sal_cfg.get("work_days", 22)))
        self.ent_sal_days.grid(row=1, column=1, sticky="w", padx=10, pady=4)

        tk.Label(grid_f, text="Số giờ làm việc / ngày:", font=("Segoe UI", 9), bg="#151a24", fg="#F8FAFC").grid(row=2, column=0, sticky="w", pady=4)
        self.ent_sal_hours = tk.Entry(grid_f, font=("Segoe UI", 9), width=16, bg="#1e2430", fg="#00FFCC", insertbackground="#fff", relief="flat")
        self.ent_sal_hours.insert(0, str(sal_cfg.get("work_hours", 8.0)))
        self.ent_sal_hours.grid(row=2, column=1, sticky="w", padx=10, pady=4)

        tk.Label(grid_f, text="Chu kỳ tính lương tháng:", font=("Segoe UI", 9, "bold"), bg="#151a24", fg="#38BDF8").grid(row=3, column=0, sticky="w", pady=4)
        cycle_box = tk.Frame(grid_f, bg="#151a24")
        cycle_box.grid(row=3, column=1, sticky="w", padx=10, pady=4)
        self.var_sal_cycle = tk.StringVar(value=sal_cfg.get("calc_cycle", "calendar_month"))
        tk.Radiobutton(cycle_box, text="Tháng dương (1 - cuối tháng)", variable=self.var_sal_cycle, value="calendar_month", font=("Segoe UI", 8), bg="#151a24", fg="#F8FAFC", selectcolor="#1e2430", activebackground="#151a24").pack(anchor="w")
        tk.Radiobutton(cycle_box, text="Chu kỳ ngày nhận lương (vd: từ mùng 5/10 đến 5/11)", variable=self.var_sal_cycle, value="payday_cycle", font=("Segoe UI", 8), bg="#151a24", fg="#38BDF8", selectcolor="#1e2430", activebackground="#151a24").pack(anchor="w")

        tk.Label(grid_f, text="Ngày nhận lương hàng tháng:", font=("Segoe UI", 9), bg="#151a24", fg="#F8FAFC").grid(row=4, column=0, sticky="w", pady=4)
        self.spin_sal_payday = tk.Spinbox(grid_f, from_=1, to=31, width=6, font=("Segoe UI", 9), bg="#1e2430", fg="#FCD34D")
        self.spin_sal_payday.delete(0, "end")
        self.spin_sal_payday.insert(0, str(self.app.config.get("payday_day", 5)))
        self.spin_sal_payday.grid(row=4, column=1, sticky="w", padx=10, pady=4)

        tk.Label(grid_f, text="💡 Giờ nghỉ trưa được quản lý tại tab 'Giờ làm & Tan làm'", font=("Segoe UI", 8, "italic"), bg="#151a24", fg="#94A3B8").grid(row=5, column=0, columnspan=2, sticky="w", pady=(6, 4))

        opt_f = tk.Frame(f, bg="#151a24")
        opt_f.pack(fill="x", pady=6)

        self.var_sal_enabled = tk.BooleanVar(value=sal_cfg.get("enabled", False))
        self.var_sal_show_daily = tk.BooleanVar(value=sal_cfg.get("show_daily", True))
        self.var_sal_show_monthly = tk.BooleanVar(value=sal_cfg.get("show_monthly", True))
        self.var_sal_hidden = tk.BooleanVar(value=sal_cfg.get("hidden", False))

        tk.Checkbutton(opt_f, text="Bật hiển thị tiền lương", variable=self.var_sal_enabled, font=("Segoe UI", 9, "bold"), bg="#151a24", fg="#10B981", selectcolor="#1e2430", activebackground="#151a24").grid(row=0, column=0, sticky="w")
        tk.Checkbutton(opt_f, text="Hiện lương hôm nay", variable=self.var_sal_show_daily, font=("Segoe UI", 8), bg="#151a24", fg="#F8FAFC", selectcolor="#1e2430", activebackground="#151a24").grid(row=0, column=1, sticky="w", padx=10)
        tk.Checkbutton(opt_f, text="Hiện lương tích lũy tháng/kỳ", variable=self.var_sal_show_monthly, font=("Segoe UI", 8), bg="#151a24", fg="#F8FAFC", selectcolor="#1e2430", activebackground="#151a24").grid(row=0, column=2, sticky="w", padx=10)
        tk.Checkbutton(opt_f, text="Che số tiền (•••••• đ)", variable=self.var_sal_hidden, font=("Segoe UI", 8), bg="#151a24", fg="#FCD34D", selectcolor="#1e2430", activebackground="#151a24").grid(row=1, column=0, sticky="w", pady=(4, 0))

        tk.Label(f, text="🎯 Task quan trọng hôm nay (Focus MIT):", font=("Segoe UI", 9, "bold"), bg="#151a24", fg="#38BDF8").pack(anchor="w", pady=(6, 2))
        task_f = tk.Frame(f, bg="#151a24")
        task_f.pack(fill="x", pady=(0, 6))

        self.ent_focus_task = tk.Entry(task_f, font=("Segoe UI", 9), bg="#1e2430", fg="#F8FAFC", insertbackground="#fff", relief="flat")
        self.ent_focus_task.insert(0, self.app.config.get("focus_task", {}).get("text", ""))
        self.ent_focus_task.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.var_task_enabled = tk.BooleanVar(value=self.app.config.get("focus_task", {}).get("enabled", False))
        tk.Checkbutton(task_f, text="Hiện task", variable=self.var_task_enabled, font=("Segoe UI", 8), bg="#151a24", fg="#F8FAFC", selectcolor="#1e2430", activebackground="#151a24").pack(side="right")

        btn_save_sal = tk.Button(
            f,
            text="💾 Lưu thiết lập Tiền Lương & Chu kỳ",
            font=("Segoe UI", 9, "bold"),
            bg="#059669",
            fg="#FFFFFF",
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self._save_salary_settings
        )
        btn_save_sal.pack(anchor="w", pady=(4, 0))

    def _save_salary_settings(self):
        try:
            mon = float(self.ent_salary_monthly.get().replace(".", "").replace(",", "").strip())
            days = int(self.ent_sal_days.get().strip())
            hrs = float(self.ent_sal_hours.get().strip())
            cyc = self.var_sal_cycle.get()
            task_txt = self.ent_focus_task.get().strip()

            p_val = int(self.spin_sal_payday.get().strip())
            if not (1 <= p_val <= 31):
                raise ValueError("Ngày nhận lương phải từ 1 đến 31!")
            self.app.config["payday_day"] = p_val

            self.app.config.setdefault("salary", {})
            self.app.config["salary"]["monthly"] = mon
            self.app.config["salary"]["work_days"] = days
            self.app.config["salary"]["work_hours"] = hrs
            self.app.config["salary"]["calc_cycle"] = cyc
            self.app.config["salary"]["enabled"] = self.var_sal_enabled.get()
            self.app.config["salary"]["show_daily"] = self.var_sal_show_daily.get()
            self.app.config["salary"]["show_monthly"] = self.var_sal_show_monthly.get()
            self.app.config["salary"]["hidden"] = self.var_sal_hidden.get()

            self.app.config.setdefault("focus_task", {})
            self.app.config["focus_task"]["text"] = task_txt
            self.app.config["focus_task"]["enabled"] = self.var_task_enabled.get() and bool(task_txt)

            self.app.save_config()
            self.app.update_extra_info_visibility()
            messagebox.showinfo("Thành công", "Đã lưu thiết lập Tiền Lương & Chu kỳ thành công!", parent=self)
        except Exception as e:
            messagebox.showerror("Lỗi", f"Thông số không hợp lệ: {e}", parent=self)

    # ---------------- 🌦️ TAB WEATHER ----------------
    def _setup_weather_tab(self):
        f = self.tab_weather
        w_cfg = self.app.config.get("weather", {})

        tk.Label(f, text="🌦️ THỜI TIẾT THỜI GIAN THỰC (OPEN-METEO)", font=("Segoe UI", 11, "bold"), bg="#151a24", fg="#38BDF8").pack(anchor="w", pady=(0, 4))
        tk.Label(f, text="Tự động cập nhật nhiệt độ, gió và tình trạng thời tiết tại địa phương.", font=("Segoe UI", 8), bg="#151a24", fg="#94A3B8").pack(anchor="w", pady=(0, 10))

        self.var_weather_enabled = tk.BooleanVar(value=w_cfg.get("enabled", True))
        tk.Checkbutton(f, text="Hiển thị thời tiết trên đồng hồ", variable=self.var_weather_enabled, font=("Segoe UI", 9, "bold"), bg="#151a24", fg="#F8FAFC", selectcolor="#1e2430", activebackground="#151a24").pack(anchor="w", pady=(0, 8))

        grid_f = tk.Frame(f, bg="#151a24")
        grid_f.pack(fill="x", pady=4)

        tk.Label(grid_f, text="Khu vực / Tỉnh thành:", font=("Segoe UI", 9), bg="#151a24", fg="#F8FAFC").grid(row=0, column=0, sticky="w", pady=4)
        cities = list(CITY_COORDINATES.keys())
        curr_city = w_cfg.get("city_name", "Hà Nội")
        self.cmb_weather_city = ttk.Combobox(grid_f, values=cities, state="readonly", width=16, font=("Segoe UI", 9))
        if curr_city in cities:
            self.cmb_weather_city.current(cities.index(curr_city))
        else:
            self.cmb_weather_city.current(0)
        self.cmb_weather_city.grid(row=0, column=1, sticky="w", padx=10, pady=4)

        tk.Label(grid_f, text="Chu kỳ tự làm mới (phút):", font=("Segoe UI", 9), bg="#151a24", fg="#F8FAFC").grid(row=1, column=0, sticky="w", pady=4)
        self.spin_weather_interval = tk.Spinbox(grid_f, from_=5, to=120, width=6, font=("Segoe UI", 9), bg="#1e2430", fg="#00FFCC")
        self.spin_weather_interval.delete(0, "end")
        self.spin_weather_interval.insert(0, str(w_cfg.get("auto_refresh_min", 30)))
        self.spin_weather_interval.grid(row=1, column=1, sticky="w", padx=10, pady=4)

        btn_save_weather = tk.Button(
            f,
            text="💾 Lưu & Cập nhật thời tiết ngay",
            font=("Segoe UI", 9, "bold"),
            bg="#2563EB",
            fg="#FFFFFF",
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self._save_weather_settings
        )
        btn_save_weather.pack(anchor="w", pady=(12, 0))

    def _save_weather_settings(self):
        sel_city = self.cmb_weather_city.get()
        interval = int(self.spin_weather_interval.get())
        enabled = self.var_weather_enabled.get()

        self.app.config.setdefault("weather", {})
        self.app.config["weather"]["city_name"] = sel_city
        self.app.config["weather"]["auto_refresh_min"] = interval
        self.app.config["weather"]["enabled"] = enabled

        if sel_city in CITY_COORDINATES:
            lat, lon = CITY_COORDINATES[sel_city]
            self.app.config["weather"]["lat"] = lat
            self.app.config["weather"]["lon"] = lon

        self.app.save_config()
        self.app.weather_mgr.fetch_weather(callback=lambda txt, d: self.app.update_extra_info_visibility(), dispatcher=self.app.root.after_idle)
        messagebox.showinfo("Thành công", "Đã lưu cài đặt thời tiết!", parent=self)

    # ---------------- 🎧 TAB FOCUS SOUND ----------------
    def _setup_focus_sound_tab(self):
        f = self.tab_focus_sound
        snd_cfg = self.app.config.get("focus_sound", {})

        tk.Label(f, text="🎧 ÂM THANH TẬP TRUNG TỰ NHIÊN (WHITE NOISE)", font=("Segoe UI", 11, "bold"), bg="#151a24", fg="#A855F7").pack(anchor="w", pady=(0, 2))
        tk.Label(f, text="Âm thanh tự nhiên êm dịu, nhẹ nhàng giúp tập trung sâu khi làm việc, không tốn tài nguyên.", font=("Segoe UI", 8), bg="#151a24", fg="#94A3B8").pack(anchor="w", pady=(0, 10))

        self.var_sound_type = tk.StringVar(value=snd_cfg.get("sound_type", "rain"))

        grid_sounds = tk.LabelFrame(f, text="🌿 Chọn loại âm thanh:", font=("Segoe UI", 9, "bold"), bg="#151a24", fg="#38BDF8", padx=10, pady=8)
        grid_sounds.pack(fill="x", pady=(0, 10))

        sound_items = list(self.app.focus_sound_mgr.SOUND_TYPES.items())
        for idx, (s_key, s_data) in enumerate(sound_items):
            r = tk.Radiobutton(
                grid_sounds,
                text=f"{s_data['icon']}  {s_data['name']}",
                variable=self.var_sound_type,
                value=s_key,
                font=("Segoe UI", 9),
                bg="#151a24",
                fg="#F8FAFC",
                selectcolor="#1e2430",
                activebackground="#151a24",
                command=self._on_sound_type_changed
            )
            r.grid(row=idx // 2, column=idx % 2, sticky="w", padx=10, pady=6)

        # Volume Slider
        vol_frame = tk.Frame(f, bg="#151a24")
        vol_frame.pack(fill="x", pady=(8, 10))
        tk.Label(vol_frame, text="🔊 Âm lượng:", font=("Segoe UI", 9, "bold"), bg="#151a24", fg="#F8FAFC").pack(side="left", padx=(0, 8))
        
        curr_vol = snd_cfg.get("volume", 50)
        self.lbl_vol_val = tk.Label(vol_frame, text=f"{curr_vol}%", font=("Consolas", 9, "bold"), bg="#151a24", fg="#00FFCC", width=5)
        self.lbl_vol_val.pack(side="right")

        def _on_vol_slide(v_str):
            v_int = int(float(v_str))
            self.lbl_vol_val.configure(text=f"{v_int}%")
            self.app.focus_sound_mgr.set_volume(v_int)
            self.app.config.setdefault("focus_sound", {})["volume"] = v_int
            self.app.save_config()

        self.scale_volume = tk.Scale(
            vol_frame,
            from_=0,
            to=100,
            orient="horizontal",
            showvalue=False,
            bg="#151a24",
            troughcolor="#1e2430",
            activebackground="#8B5CF6",
            highlightthickness=0,
            bd=0,
            cursor="hand2",
            command=_on_vol_slide
        )
        self.scale_volume.set(curr_vol)
        self.scale_volume.pack(side="left", fill="x", expand=True, padx=4)

        # Thanh trạng thái & Nút điều khiển
        self.lbl_sound_status = tk.Label(
            f,
            text=f"Trạng thái: {self.app.focus_sound_mgr.status_message}",
            font=("Segoe UI", 9, "italic"),
            bg="#151a24",
            fg="#A78BFA"
        )
        self.lbl_sound_status.pack(anchor="w", pady=(6, 8))

        btn_box = tk.Frame(f, bg="#151a24")
        btn_box.pack(fill="x", pady=(4, 0))

        is_playing = self.app.focus_sound_mgr.is_playing
        self.btn_toggle_play_sound = tk.Button(
            btn_box,
            text="⏹ DỪNG PHÁT" if is_playing else "▶ BẬT ÂM THANH TẬP TRUNG",
            font=("Segoe UI", 10, "bold"),
            bg="#EF4444" if is_playing else "#8B5CF6",
            fg="#FFFFFF",
            activebackground="#2563eb",
            activeforeground="#FFFFFF",
            relief="flat",
            padx=18,
            pady=8,
            cursor="hand2",
            command=self._toggle_focus_sound_play
        )
        self.btn_toggle_play_sound.pack(side="left")

    def _on_sound_type_changed(self):
        st = self.var_sound_type.get()
        self.app.config.setdefault("focus_sound", {})["sound_type"] = st
        self.app.save_config()
        if self.app.focus_sound_mgr.is_playing:
            self._start_playing_sound()

    def _start_playing_sound(self):
        st = self.var_sound_type.get()
        self.lbl_sound_status.configure(text="Trạng thái: ⏳ Đang khởi tạo âm thanh...", fg="#FCD34D")
        self.btn_toggle_play_sound.configure(text="⏹ DỪNG PHÁT", bg="#EF4444")

        def _on_status(success, msg):
            def _ui_update():
                if success:
                    self.lbl_sound_status.configure(text=f"Trạng thái: 🟢 {msg}", fg="#34D399")
                    self.btn_toggle_play_sound.configure(text="⏹ DỪNG PHÁT", bg="#EF4444")
                else:
                    self.lbl_sound_status.configure(text=f"Trạng thái: 🔴 {msg}", fg="#F87171")
                    self.btn_toggle_play_sound.configure(text="▶ BẬT ÂM THANH TẬP TRUNG", bg="#8B5CF6")
                self.app.update_extra_info_visibility()
            self.after_idle(_ui_update)

        self.app.focus_sound_mgr.play(st, callback=_on_status)

    def _toggle_focus_sound_play(self):
        if self.app.focus_sound_mgr.is_playing:
            self.app.focus_sound_mgr.stop()
            self.lbl_sound_status.configure(text="Trạng thái: ⚪ Đã dừng phát", fg="#94A3B8")
            self.btn_toggle_play_sound.configure(text="▶ BẬT ÂM THANH TẬP TRUNG", bg="#8B5CF6")
            self.app.update_extra_info_visibility()
        else:
            self._start_playing_sound()

    # ---------------- 📅 TAB MILESTONES ----------------
    def _setup_milestones_tab(self):
        f = self.tab_milestones
        tk.Label(f, text="📅 ĐẾM NGƯỢC NGÀY NHẬN LƯƠNG & CÁC DỊP LỄ QUAN TRỌNG", font=("Segoe UI", 11, "bold"), bg="#151a24", fg="#F59E0B").pack(anchor="w", pady=(0, 4))

        self.tree_milestones = ttk.Treeview(f, columns=("name", "days", "date"), show="headings", height=8)
        self.tree_milestones.heading("name", text="Dịp lễ / Cột mốc")
        self.tree_milestones.heading("days", text="Còn lại")
        self.tree_milestones.heading("date", text="Ngày diễn ra")
        self.tree_milestones.column("name", width=260)
        self.tree_milestones.column("days", width=110, anchor="center")
        self.tree_milestones.column("date", width=120, anchor="center")
        self.tree_milestones.pack(fill="both", expand=True, pady=4)

        # Form thêm dịp lễ mới
        add_frame = tk.LabelFrame(f, text="➕ Thêm dịp lễ / Ngày kỷ niệm mới", font=("Segoe UI", 9, "bold"), bg="#151a24", fg="#38BDF8", padx=8, pady=6)
        add_frame.pack(fill="x", pady=(4, 6))

        tk.Label(add_frame, text="Tên dịp lễ:", font=("Segoe UI", 9), bg="#151a24", fg="#F8FAFC").grid(row=0, column=0, sticky="w", padx=(0, 4))
        self.ent_new_holiday_name = tk.Entry(add_frame, font=("Segoe UI", 9), width=22, bg="#1e2430", fg="#F8FAFC", insertbackground="#fff", relief="flat")
        self.ent_new_holiday_name.grid(row=0, column=1, sticky="w", padx=(0, 10))

        tk.Label(add_frame, text="Ngày:", font=("Segoe UI", 9), bg="#151a24", fg="#F8FAFC").grid(row=0, column=2, sticky="w", padx=(0, 2))
        self.spin_new_holiday_day = tk.Spinbox(add_frame, from_=1, to=31, width=3, font=("Segoe UI", 9), bg="#1e2430", fg="#00FFCC")
        self.spin_new_holiday_day.delete(0, "end")
        self.spin_new_holiday_day.insert(0, "1")
        self.spin_new_holiday_day.grid(row=0, column=3, sticky="w", padx=(0, 8))

        tk.Label(add_frame, text="Tháng:", font=("Segoe UI", 9), bg="#151a24", fg="#F8FAFC").grid(row=0, column=4, sticky="w", padx=(0, 2))
        self.spin_new_holiday_month = tk.Spinbox(add_frame, from_=1, to=12, width=3, font=("Segoe UI", 9), bg="#1e2430", fg="#00FFCC")
        self.spin_new_holiday_month.delete(0, "end")
        self.spin_new_holiday_month.insert(0, "1")
        self.spin_new_holiday_month.grid(row=0, column=5, sticky="w", padx=(0, 10))

        btn_add_hol = tk.Button(
            add_frame,
            text="➕ Thêm",
            font=("Segoe UI", 8, "bold"),
            bg="#059669",
            fg="#FFFFFF",
            relief="flat",
            padx=10,
            pady=3,
            cursor="hand2",
            command=self._add_custom_holiday
        )
        btn_add_hol.grid(row=0, column=6, sticky="w")

        # Nút quản lý
        act_frame = tk.Frame(f, bg="#151a24")
        act_frame.pack(fill="x", pady=(0, 4))

        btn_del_hol = tk.Button(
            act_frame,
            text="🗑️ Xóa dịp lễ đã chọn",
            font=("Segoe UI", 8, "bold"),
            bg="#334155",
            fg="#CBD5E1",
            relief="flat",
            padx=10,
            pady=4,
            cursor="hand2",
            command=self._delete_selected_holiday
        )
        btn_del_hol.pack(side="left", padx=(0, 8))

        btn_reset_hol = tk.Button(
            act_frame,
            text="🔄 Khôi phục lễ mặc định",
            font=("Segoe UI", 8),
            bg="#1e2430",
            fg="#94A3B8",
            relief="flat",
            padx=10,
            pady=4,
            cursor="hand2",
            command=self._reset_default_holidays
        )
        btn_reset_hol.pack(side="left")

        self._populate_milestones_list()

    def _populate_milestones_list(self):
        for item in self.tree_milestones.get_children():
            self.tree_milestones.delete(item)

        now = datetime.now()

        # 1. Cột mốc ngày nhận lương tiếp theo
        payday = self.app.config.get("payday_day", 5)
        p_days, p_date = get_payday_countdown_info(now, payday)
        if p_date:
            self.tree_milestones.insert("", "end", values=("💰 Ngày nhận lương tiếp theo", f"⏳ {p_days} ngày", p_date))

        # 2. Danh sách các ngày lễ từ cấu hình
        holidays = self.app.config.get("holidays", HOLIDAYS_DATA)
        computed_events = []
        for idx, h in enumerate(holidays):
            try:
                m = int(h.get("month", 1))
                d = int(h.get("day", 1))
                dt = datetime(now.year, m, d)
                if dt < now:
                    dt = datetime(now.year + 1, m, d)
                computed_events.append((h.get("name", "Dịp lễ"), dt, idx))
            except Exception:
                pass

        # Sort theo thứ tự thời gian gần nhất
        for name, dt, idx in sorted(computed_events, key=lambda x: x[1]):
            diff_d = int(math.ceil((dt - now).total_seconds() / 86400.0))
            self.tree_milestones.insert("", "end", values=(name, f"⏳ {diff_d} ngày", dt.strftime("%d/%m/%Y")), tags=(str(idx),))

    def _add_custom_holiday(self):
        name = self.ent_new_holiday_name.get().strip()
        if not name:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập tên dịp lễ!", parent=self)
            return

        try:
            d = int(self.spin_new_holiday_day.get().strip())
            m = int(self.spin_new_holiday_month.get().strip())
            if not (1 <= m <= 12 and 1 <= d <= 31):
                raise ValueError("Ngày hoặc tháng không hợp lệ!")
            datetime(2024, m, d)
        except Exception as e:
            messagebox.showerror("Lỗi", f"Ngày tháng không hợp lệ: {e}", parent=self)
            return

        holidays = list(self.app.config.get("holidays", HOLIDAYS_DATA))
        holidays.append({"name": name, "month": m, "day": d})
        self.app.config["holidays"] = holidays
        self.app.save_config()
        self._populate_milestones_list()
        self.ent_new_holiday_name.delete(0, "end")
        messagebox.showinfo("Thành công", f"Đã thêm dịp lễ: {name} ({d:02d}/{m:02d})", parent=self)

    def _delete_selected_holiday(self):
        selected = self.tree_milestones.selection()
        if not selected:
            messagebox.showwarning("Cảnh báo", "Vui lòng bấm chọn một dịp lễ trong bảng để xóa!", parent=self)
            return

        item_vals = self.tree_milestones.item(selected[0], "values")
        if not item_vals:
            return

        name_to_del = item_vals[0]
        if "Ngày nhận lương" in name_to_del:
            messagebox.showinfo("Thông báo", "Ngày nhận lương được cấu hình tại tab 'Tiền Lương', không thể xóa ở đây.", parent=self)
            return

        if not messagebox.askyesno("Xác nhận", f"Bạn có chắc muốn xóa dịp lễ '{name_to_del}'?", parent=self):
            return

        holidays = list(self.app.config.get("holidays", HOLIDAYS_DATA))
        new_holidays = [h for h in holidays if h.get("name") != name_to_del]
        self.app.config["holidays"] = new_holidays
        self.app.save_config()
        self._populate_milestones_list()
        messagebox.showinfo("Thành công", f"Đã xóa dịp lễ '{name_to_del}'!", parent=self)

    def _reset_default_holidays(self):
        if not messagebox.askyesno("Xác nhận", "Khôi phục lại danh sách các dịp lễ lớn mặc định của Việt Nam?", parent=self):
            return
        self.app.config["holidays"] = list(HOLIDAYS_DATA)
        self.app.save_config()
        self._populate_milestones_list()
        messagebox.showinfo("Thành công", "Đã khôi phục danh sách dịp lễ mặc định!", parent=self)

    # ---------------- ⏳ TAB TIMER ----------------
    def _setup_timer_tab(self):
        f = self.tab_timer
        tk.Label(f, text="⏳ ĐẶT THỜI GIAN ĐẾM NGƯỢC", font=("Segoe UI", 11, "bold"), bg="#151a24", fg="#38BDF8").pack(anchor="w", pady=(0, 8))

        preset_frame = tk.Frame(f, bg="#151a24")
        preset_frame.pack(fill="x", pady=(0, 10))

        presets = [
            ("1 Phút", 60), ("3 Phút", 180), ("5 Phút", 300), ("10 Phút", 600),
            ("15 Phút", 900), ("25 Phút", 1500), ("30 Phút", 1800), ("1 Giờ", 3600)
        ]
        row, col = 0, 0
        for name, sec in presets:
            btn = tk.Button(
                preset_frame,
                text=name,
                font=("Segoe UI", 9, "bold"),
                bg="#1e2430",
                fg="#38BDF8",
                activebackground="#2563EB",
                activeforeground="#FFFFFF",
                relief="flat",
                padx=8,
                pady=6,
                cursor="hand2",
                command=lambda s=sec: self._set_timer_preset(s)
            )
            btn.grid(row=row, column=col, padx=4, pady=4, sticky="ew")
            col += 1
            if col > 3:
                col = 0
                row += 1
        for c in range(4):
            preset_frame.grid_columnconfigure(c, weight=1)

        custom_box = tk.Frame(f, bg="#151a24")
        custom_box.pack(fill="x", pady=6)

        tk.Label(custom_box, text="Tùy chỉnh: Phút:", font=("Segoe UI", 9), bg="#151a24", fg="#F8FAFC").pack(side="left")
        self.spin_tm_m = tk.Spinbox(custom_box, from_=0, to=300, width=5, font=("Segoe UI", 9), bg="#1e2430", fg="#00FFCC")
        self.spin_tm_m.delete(0, "end")
        self.spin_tm_m.insert(0, "5")
        self.spin_tm_m.pack(side="left", padx=4)

        tk.Label(custom_box, text="Giây:", font=("Segoe UI", 9), bg="#151a24", fg="#F8FAFC").pack(side="left")
        self.spin_tm_s = tk.Spinbox(custom_box, from_=0, to=59, width=4, font=("Segoe UI", 9), bg="#1e2430", fg="#00FFCC")
        self.spin_tm_s.delete(0, "end")
        self.spin_tm_s.insert(0, "0")
        self.spin_tm_s.pack(side="left", padx=4)

        btn_apply_tm = tk.Button(
            custom_box,
            text="Áp dụng",
            font=("Segoe UI", 8, "bold"),
            bg="#2563EB",
            fg="#FFFFFF",
            relief="flat",
            padx=10,
            pady=3,
            cursor="hand2",
            command=self._apply_custom_timer
        )
        btn_apply_tm.pack(side="left", padx=8)

        ctrl_frame = tk.Frame(f, bg="#151a24")
        ctrl_frame.pack(fill="x", pady=10)

        self.btn_timer_toggle = tk.Button(
            ctrl_frame,
            text="▶ BẮT ĐẦU ĐẾM",
            font=("Segoe UI", 11, "bold"),
            bg="#10B981",
            fg="#FFFFFF",
            relief="flat",
            padx=14,
            pady=8,
            cursor="hand2",
            command=self._toggle_timer
        )
        self.btn_timer_toggle.pack(side="left", expand=True, fill="x", padx=3)

        btn_timer_reset = tk.Button(
            ctrl_frame,
            text="🔄 Đặt lại",
            font=("Segoe UI", 10, "bold"),
            bg="#475569",
            fg="#FFFFFF",
            relief="flat",
            padx=12,
            pady=8,
            cursor="hand2",
            command=self._reset_timer
        )
        btn_timer_reset.pack(side="left", padx=3)
        self._update_timer_button_state()

    def _set_timer_preset(self, sec):
        self.app.set_timer_seconds(sec)
        if self.app.config.get("mode") != "timer":
            self.app.switch_mode("timer")
        self._update_timer_button_state()

    def _apply_custom_timer(self):
        try:
            m = int(self.spin_tm_m.get())
            s = int(self.spin_tm_s.get())
            total = m * 60 + s
            if total <= 0:
                raise ValueError()
            self.app.set_timer_seconds(total)
            if self.app.config.get("mode") != "timer":
                self.app.switch_mode("timer")
            self._update_timer_button_state()
        except Exception:
            messagebox.showerror("Lỗi", "Thời gian không hợp lệ!", parent=self)

    def _toggle_timer(self):
        if self.app.config.get("mode") != "timer":
            self.app.switch_mode("timer")
        if self.app.timer_state == "running":
            self.app.pause_timer()
        else:
            self.app.start_timer()
        self._update_timer_button_state()

    def _reset_timer(self):
        self.app.reset_timer()
        self._update_timer_button_state()

    def _update_timer_button_state(self):
        if self.app.timer_state == "running":
            self.btn_timer_toggle.configure(text="⏸ TẠM DỪNG", bg="#F59E0B")
        else:
            self.btn_timer_toggle.configure(text="▶ TIẾP TỤC / BẮT ĐẦU", bg="#10B981")

    # ---------------- ⏰ TAB ALARMS ----------------
    def _setup_alarm_tab(self):
        f = self.tab_alarm
        tk.Label(f, text="⏰ DANH SÁCH BÁO THỨC", font=("Segoe UI", 11, "bold"), bg="#151a24", fg="#EC4899").pack(anchor="w", pady=(0, 6))

        add_box = tk.Frame(f, bg="#151a24")
        add_box.pack(fill="x", pady=(0, 10))

        tk.Label(add_box, text="Giờ:", font=("Segoe UI", 9), bg="#151a24", fg="#f1f5f9").pack(side="left")
        self.spin_alm_h = tk.Spinbox(add_box, from_=0, to=23, width=3, font=("Segoe UI", 9), bg="#1e2430", fg="#EC4899")
        self.spin_alm_h.delete(0, "end")
        self.spin_alm_h.insert(0, "07")
        self.spin_alm_h.pack(side="left", padx=2)

        tk.Label(add_box, text="Phút:", font=("Segoe UI", 9), bg="#151a24", fg="#f1f5f9").pack(side="left")
        self.spin_alm_m = tk.Spinbox(add_box, from_=0, to=59, width=3, font=("Segoe UI", 9), bg="#1e2430", fg="#EC4899")
        self.spin_alm_m.delete(0, "end")
        self.spin_alm_m.insert(0, "00")
        self.spin_alm_m.pack(side="left", padx=2)

        tk.Label(add_box, text="Ghi chú:", font=("Segoe UI", 9), bg="#151a24", fg="#f1f5f9").pack(side="left", padx=(6, 2))
        self.ent_alm_lbl = tk.Entry(add_box, font=("Segoe UI", 9), width=18, bg="#1e2430", fg="#f1f5f9", insertbackground="#fff", relief="flat")
        self.ent_alm_lbl.insert(0, "Báo thức mới")
        self.ent_alm_lbl.pack(side="left", padx=4)

        btn_add = tk.Button(
            add_box,
            text="➕ Thêm",
            font=("Segoe UI", 8, "bold"),
            bg="#EC4899",
            fg="#FFFFFF",
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=self._add_alarm
        )
        btn_add.pack(side="right")

        self.alarm_items_frame = tk.Frame(f, bg="#151a24")
        self.alarm_items_frame.pack(fill="both", expand=True)
        self._render_alarm_list()

    def _render_alarm_list(self):
        for widget in self.alarm_items_frame.winfo_children():
            widget.destroy()

        alarms = self.app.config.get("alarms", [])
        if not alarms:
            lbl_empty = tk.Label(self.alarm_items_frame, text="Chưa có báo thức nào được tạo.", font=("Segoe UI", 10, "italic"), bg="#151a24", fg="#64748b")
            lbl_empty.pack(pady=20)
            return

        for idx, alm in enumerate(alarms):
            row_f = tk.Frame(self.alarm_items_frame, bg="#1a202c", padx=10, pady=6, highlightthickness=1, highlightbackground="#2d3748")
            row_f.pack(fill="x", pady=2)

            is_on = alm.get("enabled", False)
            btn_toggle_text = "🟢 BẬT" if is_on else "⚪ TẮT"
            btn_toggle_bg = "#059669" if is_on else "#475569"

            btn_toggle = tk.Button(
                row_f,
                text=btn_toggle_text,
                font=("Segoe UI", 8, "bold"),
                bg=btn_toggle_bg,
                fg="#ffffff",
                relief="flat",
                padx=8,
                pady=2,
                cursor="hand2",
                command=lambda a_idx=idx: self._toggle_alarm_state(a_idx)
            )
            btn_toggle.pack(side="left", padx=(0, 10))

            lbl_time = tk.Label(row_f, text=alm.get("time", "00:00"), font=("Consolas", 12, "bold"), bg="#1a202c", fg="#EC4899" if is_on else "#94a3b8")
            lbl_time.pack(side="left", padx=(0, 12))

            lbl_label = tk.Label(row_f, text=alm.get("label", "Báo thức"), font=("Segoe UI", 9), bg="#1a202c", fg="#f1f5f9" if is_on else "#64748b")
            lbl_label.pack(side="left", fill="x", expand=True)

            btn_del = tk.Button(
                row_f,
                text="🗑️",
                font=("Segoe UI Emoji", 9),
                bg="#1a202c",
                fg="#EF4444",
                activebackground="#EF4444",
                activeforeground="#ffffff",
                relief="flat",
                cursor="hand2",
                command=lambda a_idx=idx: self._delete_alarm(a_idx)
            )
            btn_del.pack(side="right")

    def _add_alarm(self):
        try:
            h = int(self.spin_alm_h.get())
            m = int(self.spin_alm_m.get())
            if not (0 <= h <= 23 and 0 <= m <= 59):
                raise ValueError()
            t_str = f"{h:02d}:{m:02d}"
            lbl = self.ent_alm_lbl.get().strip() or "Báo thức"
            alarms = self.app.config.setdefault("alarms", [])
            import time
            alarms.append({
                "id": int(time.time()),
                "time": t_str,
                "label": lbl,
                "enabled": True,
                "repeat": True
            })
            self.app.save_config()
            self._render_alarm_list()
        except Exception:
            messagebox.showerror("Lỗi", "Giờ hoặc phút không hợp lệ!", parent=self)

    def _toggle_alarm_state(self, idx):
        alarms = self.app.config.get("alarms", [])
        if 0 <= idx < len(alarms):
            alarms[idx]["enabled"] = not alarms[idx].get("enabled", False)
            self.app.save_config()
            self._render_alarm_list()

    def _delete_alarm(self, idx):
        alarms = self.app.config.get("alarms", [])
        if 0 <= idx < len(alarms):
            alarms.pop(idx)
            self.app.save_config()
            self._render_alarm_list()

    # ---------------- ⏱️ TAB STOPWATCH ----------------
    def _setup_stopwatch_tab(self):
        f = self.tab_stopwatch
        tk.Label(f, text="⏱️ BẤM GIỜ THỂ THAO & ĐO THỜI GIAN (STOPWATCH)", font=("Segoe UI", 11, "bold"), bg="#151a24", fg="#10B981").pack(anchor="w", pady=(0, 8))

        ctrl_frame = tk.Frame(f, bg="#151a24")
        ctrl_frame.pack(fill="x", pady=(0, 10))

        self.btn_sw_toggle = tk.Button(
            ctrl_frame,
            text="▶ BẮT ĐẦU BẤM GIỜ",
            font=("Segoe UI", 11, "bold"),
            bg="#10B981",
            fg="#FFFFFF",
            relief="flat",
            padx=14,
            pady=8,
            cursor="hand2",
            command=self._toggle_stopwatch
        )
        self.btn_sw_toggle.pack(side="left", expand=True, fill="x", padx=3)

        self.btn_sw_lap = tk.Button(
            ctrl_frame,
            text="🚩 Ghi vòng (Lap)",
            font=("Segoe UI", 10, "bold"),
            bg="#2563EB",
            fg="#FFFFFF",
            relief="flat",
            padx=10,
            pady=8,
            cursor="hand2",
            command=self._sw_lap
        )
        self.btn_sw_lap.pack(side="left", padx=3)

        btn_sw_reset = tk.Button(
            ctrl_frame,
            text="🔄 Đặt lại",
            font=("Segoe UI", 10, "bold"),
            bg="#475569",
            fg="#FFFFFF",
            relief="flat",
            padx=10,
            pady=8,
            cursor="hand2",
            command=self._sw_reset
        )
        btn_sw_reset.pack(side="left", padx=3)

        tk.Label(f, text="Danh sách các vòng bấm giờ:", font=("Segoe UI", 9, "bold"), bg="#151a24", fg="#94a3b8").pack(anchor="w", pady=(4, 2))

        self.sw_lap_text = tk.Text(f, height=8, bg="#0f172a", fg="#38bdf8", font=("Consolas", 9), relief="flat", padx=8, pady=6)
        self.sw_lap_text.pack(fill="both", expand=True)
        self._render_sw_laps()
        self._update_sw_button_state()

    def _toggle_stopwatch(self):
        if self.app.config.get("mode") != "stopwatch":
            self.app.switch_mode("stopwatch")
        if self.app.stopwatch_running:
            self.app.pause_stopwatch()
        else:
            self.app.start_stopwatch()
        self._update_sw_button_state()

    def _sw_lap(self):
        self.app.lap_stopwatch()
        self._render_sw_laps()

    def _sw_reset(self):
        self.app.reset_stopwatch()
        self._render_sw_laps()
        self._update_sw_button_state()

    def _render_sw_laps(self):
        self.sw_lap_text.delete("1.0", "end")
        if not self.app.stopwatch_laps:
            self.sw_lap_text.insert("end", "Chưa có vòng bấm giờ nào.\nNhấn 'Ghi vòng (Lap)' trong khi bấm giờ để lưu mốc.")
            return
        for idx, lap in enumerate(reversed(self.app.stopwatch_laps), 1):
            self.sw_lap_text.insert("end", f"🚩 Vòng #{len(self.app.stopwatch_laps) - idx + 1:02d}:  Vòng: {lap['lap_str']}  |  Tổng: {lap['total_str']}\n")

    def _update_sw_button_state(self):
        if self.app.stopwatch_running:
            self.btn_sw_toggle.configure(text="⏸ TẠM DỪNG", bg="#F59E0B")
        else:
            self.btn_sw_toggle.configure(text="▶ BẮT ĐẦU BẤM GIỜ", bg="#10B981")

    # ---------------- 🍅 TAB POMODORO ----------------
    def _setup_pomodoro_tab(self):
        f = self.tab_pomodoro
        tk.Label(f, text="🍅 PHƯƠNG PHÁP QUẢN TRỊ THỜI GIAN (POMODORO)", font=("Segoe UI", 11, "bold"), bg="#151a24", fg="#EF4444").pack(anchor="w", pady=(0, 6))
        tk.Label(f, text="Làm việc tập trung 25 phút, nghỉ ngắn 5 phút. Sau mỗi 4 chu kỳ nghỉ dài 15 phút.", font=("Segoe UI", 8), bg="#151a24", fg="#94A3B8").pack(anchor="w", pady=(0, 10))

        grid_f = tk.Frame(f, bg="#151a24")
        grid_f.pack(fill="x", pady=4)

        tk.Label(grid_f, text="Thời gian tập trung (phút):", font=("Segoe UI", 9), bg="#151a24", fg="#F8FAFC").grid(row=0, column=0, sticky="w", pady=4)
        self.spin_pomo_work = tk.Spinbox(grid_f, from_=1, to=120, width=6, font=("Segoe UI", 9), bg="#1e2430", fg="#EF4444")
        self.spin_pomo_work.delete(0, "end")
        self.spin_pomo_work.insert(0, str(self.app.config.get("pomo_work_min", 25)))
        self.spin_pomo_work.grid(row=0, column=1, sticky="w", padx=10, pady=4)

        tk.Label(grid_f, text="Nghỉ ngắn (phút):", font=("Segoe UI", 9), bg="#151a24", fg="#F8FAFC").grid(row=1, column=0, sticky="w", pady=4)
        self.spin_pomo_break = tk.Spinbox(grid_f, from_=1, to=60, width=6, font=("Segoe UI", 9), bg="#1e2430", fg="#10B981")
        self.spin_pomo_break.delete(0, "end")
        self.spin_pomo_break.insert(0, str(self.app.config.get("pomo_break_min", 5)))
        self.spin_pomo_break.grid(row=1, column=1, sticky="w", padx=10, pady=4)

        tk.Label(grid_f, text="Nghỉ dài (phút):", font=("Segoe UI", 9), bg="#151a24", fg="#F8FAFC").grid(row=2, column=0, sticky="w", pady=4)
        self.spin_pomo_long = tk.Spinbox(grid_f, from_=1, to=60, width=6, font=("Segoe UI", 9), bg="#1e2430", fg="#38BDF8")
        self.spin_pomo_long.delete(0, "end")
        self.spin_pomo_long.insert(0, str(self.app.config.get("pomo_long_break_min", 15)))
        self.spin_pomo_long.grid(row=2, column=1, sticky="w", padx=10, pady=4)

        btn_save_pomo = tk.Button(
            f,
            text="💾 Áp dụng thiết lập Pomodoro",
            font=("Segoe UI", 9, "bold"),
            bg="#2563EB",
            fg="#FFFFFF",
            relief="flat",
            padx=12,
            pady=5,
            cursor="hand2",
            command=self._apply_pomodoro_settings
        )
        btn_save_pomo.pack(anchor="w", pady=(10, 12))

        btn_start_pomo = tk.Button(
            f,
            text="🍅 BẮT ĐẦU PHIÊN POMODORO MỚI",
            font=("Segoe UI", 10, "bold"),
            bg="#EF4444",
            fg="#FFFFFF",
            relief="flat",
            padx=14,
            pady=8,
            cursor="hand2",
            command=self._start_pomodoro
        )
        btn_start_pomo.pack(fill="x", pady=4)

    def _apply_pomodoro_settings(self):
        try:
            w_val = int(self.spin_pomo_work.get())
            b_val = int(self.spin_pomo_break.get())
            l_val = int(self.spin_pomo_long.get())
            self.app.config["pomo_work_min"] = w_val
            self.app.config["pomo_break_min"] = b_val
            self.app.config["pomo_long_break_min"] = l_val
            self.app.save_config()
            messagebox.showinfo("Thành công", "Đã lưu cài đặt Pomodoro!", parent=self)
        except Exception:
            messagebox.showerror("Lỗi", "Số phút không hợp lệ!", parent=self)

    def _start_pomodoro(self):
        self._apply_pomodoro_settings()
        self.app.switch_mode("pomodoro")
        self.app.start_pomodoro_work()

    # ---------------- 🎨 TAB DISPLAY & AI ----------------
    def _setup_display_tab(self):
        f = self.tab_display
        tk.Label(f, text="🎨 TÙY BIẾN GIAO DIỆN & AI ĐỘNG VIÊN", font=("Segoe UI", 11, "bold"), bg="#151a24", fg="#F59E0B").pack(anchor="w", pady=(0, 6))

        mascots = ["🚀", "☕", "🐱", "💎", "🔋", "🎯", "🔥", "None"]
        m_frame = tk.Frame(f, bg="#151a24")
        m_frame.pack(fill="x", pady=2)
        tk.Label(m_frame, text="Linh vật:", font=("Segoe UI", 9), bg="#151a24", fg="#F8FAFC").pack(side="left")
        for m in mascots:
            btn = tk.Button(
                m_frame,
                text=m,
                font=("Segoe UI Emoji", 10),
                bg="#1e2430",
                fg="#F8FAFC",
                relief="flat",
                padx=6,
                pady=2,
                cursor="hand2",
                command=lambda val=m: self._select_mascot(val)
            )
            btn.pack(side="left", padx=2)

        chk_f = tk.Frame(f, bg="#151a24")
        chk_f.pack(fill="x", pady=6)

        self.var_mini_mode = tk.BooleanVar(value=self.app.config.get("mini_mode", False))
        self.var_dynamic_color = tk.BooleanVar(value=self.app.config.get("dynamic_time_color", True))
        self.var_autostart = tk.BooleanVar(value=is_start_with_windows())
        self.var_sys_monitor = tk.BooleanVar(value=self.app.config.get("show_sys_monitor", False))
        self.var_autohide = tk.BooleanVar(value=self.app.config.get("auto_hide", False))
        self.var_quote = tk.BooleanVar(value=self.app.config.get("show_quote", True))
        self.var_water = tk.BooleanVar(value=self.app.config.get("water_reminder", {}).get("enabled", True))
        self.var_progress = tk.BooleanVar(value=self.app.config.get("show_progress", True))
        self.var_sound = tk.BooleanVar(value=self.app.config.get("sound_enabled", True))

        tk.Checkbutton(chk_f, text="Chế độ thu nhỏ (Mini Mode)", variable=self.var_mini_mode, font=("Segoe UI", 8), bg="#151a24", fg="#F8FAFC", selectcolor="#1e2430", activebackground="#151a24", command=self._toggle_mini_mode_setting).grid(row=0, column=0, sticky="w")
        tk.Checkbutton(chk_f, text="Tự đổi màu theo thời gian", variable=self.var_dynamic_color, font=("Segoe UI", 8), bg="#151a24", fg="#F8FAFC", selectcolor="#1e2430", activebackground="#151a24", command=self._toggle_dynamic_color_setting).grid(row=0, column=1, sticky="w", padx=8)
        tk.Checkbutton(chk_f, text="Khởi động cùng Windows", variable=self.var_autostart, font=("Segoe UI", 8), bg="#151a24", fg="#38BDF8", selectcolor="#1e2430", activebackground="#151a24", command=self._toggle_autostart_setting).grid(row=0, column=2, sticky="w", padx=8)
        tk.Checkbutton(chk_f, text="Giám sát CPU & RAM", variable=self.var_sys_monitor, font=("Segoe UI", 8), bg="#151a24", fg="#F8FAFC", selectcolor="#1e2430", activebackground="#151a24", command=self._toggle_sys_monitor_setting).grid(row=1, column=0, sticky="w", pady=2)
        tk.Checkbutton(chk_f, text="Tự làm mờ khi rời chuột (Auto-Hide)", variable=self.var_autohide, font=("Segoe UI", 8), bg="#151a24", fg="#F8FAFC", selectcolor="#1e2430", activebackground="#151a24", command=self._toggle_autohide_setting).grid(row=1, column=1, sticky="w", padx=8, pady=2)
        tk.Checkbutton(chk_f, text="Hiện câu nói động viên GenZ", variable=self.var_quote, font=("Segoe UI", 8), bg="#151a24", fg="#F8FAFC", selectcolor="#1e2430", activebackground="#151a24", command=self._toggle_quote_setting).grid(row=1, column=2, sticky="w", padx=8, pady=2)
        tk.Checkbutton(chk_f, text="Nhắc nhở uống nước (45p)", variable=self.var_water, font=("Segoe UI", 8), bg="#151a24", fg="#F8FAFC", selectcolor="#1e2430", activebackground="#151a24", command=self._toggle_water_setting).grid(row=2, column=0, sticky="w")
        tk.Checkbutton(chk_f, text="Hiện thanh tiến độ ngày làm", variable=self.var_progress, font=("Segoe UI", 8), bg="#151a24", fg="#F8FAFC", selectcolor="#1e2430", activebackground="#151a24", command=self._toggle_progress_setting).grid(row=2, column=1, sticky="w", padx=8)
        tk.Checkbutton(chk_f, text="Bật âm thanh / Chuông báo", variable=self.var_sound, font=("Segoe UI", 8), bg="#151a24", fg="#F8FAFC", selectcolor="#1e2430", activebackground="#151a24", command=self._toggle_sound_setting).grid(row=2, column=2, sticky="w", padx=8)

        self.var_mascot_cat = tk.BooleanVar(value=self.app.config.get("show_mascot", True))
        tk.Checkbutton(chk_f, text="🐱 Hiện thú cưng Pixel Cat", variable=self.var_mascot_cat, font=("Segoe UI", 8, "bold"), bg="#151a24", fg="#FCD34D", selectcolor="#1e2430", activebackground="#151a24", command=self._toggle_mascot_cat_setting).grid(row=3, column=0, columnspan=2, sticky="w", pady=(2, 0))

        ai_box = tk.LabelFrame(f, text="🤖 Cấu hình AI Sinh Câu Động Viên GenZ (Gemini / OpenAI)", font=("Segoe UI", 9, "bold"), bg="#151a24", fg="#38BDF8", padx=10, pady=8)
        ai_box.pack(fill="x", pady=(6, 0))

        ai_cfg = self.app.config.get("ai_quotes", {})
        tk.Label(ai_box, text="Provider:", font=("Segoe UI", 8), bg="#151a24", fg="#F8FAFC").grid(row=0, column=0, sticky="w")
        self.cmb_ai_prov = ttk.Combobox(ai_box, values=["gemini", "openai", "groq", "openrouter", "custom"], state="readonly", width=12, font=("Segoe UI", 8))
        self.cmb_ai_prov.set(ai_cfg.get("provider", "gemini"))
        self.cmb_ai_prov.grid(row=0, column=1, sticky="w", padx=6, pady=2)

        tk.Label(ai_box, text="API Key:", font=("Segoe UI", 8), bg="#151a24", fg="#F8FAFC").grid(row=0, column=2, sticky="w", padx=(10, 2))
        self.ent_ai_key = tk.Entry(ai_box, font=("Segoe UI", 8), width=24, show="*", bg="#1e2430", fg="#38BDF8", insertbackground="#fff", relief="flat")
        self.ent_ai_key.insert(0, ai_cfg.get("api_key", ""))
        self.ent_ai_key.grid(row=0, column=3, sticky="w", padx=4, pady=2)

        btn_save_ai = tk.Button(
            ai_box,
            text="Lưu Key",
            font=("Segoe UI", 8, "bold"),
            bg="#2563EB",
            fg="#FFFFFF",
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2",
            command=self._save_ai_config
        )
        btn_save_ai.grid(row=0, column=4, sticky="w", padx=6)

        btn_test_ai = tk.Button(
            ai_box,
            text="Thử nghiệm sinh câu AI",
            font=("Segoe UI", 8),
            bg="#475569",
            fg="#FFFFFF",
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2",
            command=self._test_ai_generation
        )
        btn_test_ai.grid(row=1, column=1, columnspan=2, sticky="w", pady=4)

        self.lbl_ai_status = tk.Label(ai_box, text="Trạng thái AI: Sẵn sàng", font=("Segoe UI", 8, "italic"), bg="#151a24", fg="#94A3B8")
        self.lbl_ai_status.grid(row=1, column=3, columnspan=2, sticky="w", padx=4, pady=4)

    def _select_mascot(self, mascot):
        val = "" if mascot == "None" else mascot
        self.app.config["mascot"] = val
        self.app.save_config()

    def _toggle_mascot_cat_setting(self):
        self.app.config["show_mascot"] = self.var_mascot_cat.get()
        self.app.update_mascot_visibility()
        self.app.save_config()

    def _save_ai_config(self):
        prov = self.cmb_ai_prov.get().strip()
        key = self.ent_ai_key.get().strip()
        self.app.config.setdefault("ai_quotes", {})
        self.app.config["ai_quotes"]["provider"] = prov
        self.app.config["ai_quotes"]["api_key"] = key
        self.app.save_config()
        messagebox.showinfo("Thành công", "Đã lưu thông tin cấu hình AI API!", parent=self)

    def _test_ai_generation(self):
        self._save_ai_config()
        self.lbl_ai_status.configure(text="Đang kết nối AI sinh câu GenZ...", fg="#38BDF8")

        def _on_result(quote, is_ai, error):
            if not self.winfo_exists():
                return
            if is_ai and quote:
                self.lbl_ai_status.configure(text=f"✨ Thành công: \"{quote[:40]}...\"", fg="#10B981")
                self.app.current_quote = quote
            else:
                msg = f"⚠️ Lỗi API: {error}" if error else f"✨ Đã đổi câu: \"{quote[:40]}...\""
                self.lbl_ai_status.configure(text=msg[:70], fg="#FCD34D")
                self.app.current_quote = quote

        self.app.ai_mgr.fetch_ai_quote("afternoon", callback=_on_result, dispatcher=self.app.root.after_idle)

    def _toggle_mini_mode_setting(self):
        val = self.var_mini_mode.get()
        self.app.config["mini_mode"] = val
        self.app.apply_mini_mode()
        self.app.save_config()

    def _toggle_dynamic_color_setting(self):
        val = self.var_dynamic_color.get()
        self.app.config["dynamic_time_color"] = val
        self.app.save_config()

    def _toggle_autostart_setting(self):
        val = self.var_autostart.get()
        success = set_start_with_windows(val)
        if success:
            msg = "Đã bật tự khởi động cùng Windows!" if val else "Đã tắt tự khởi động cùng Windows!"
            messagebox.showinfo("Thành công", msg, parent=self)
        else:
            messagebox.showerror("Lỗi", "Không thể ghi vào Windows Registry!", parent=self)

    def _toggle_sys_monitor_setting(self):
        val = self.var_sys_monitor.get()
        self.app.config["show_sys_monitor"] = val
        self.app.update_extra_info_visibility()
        self.app.save_config()

    def _toggle_autohide_setting(self):
        val = self.var_autohide.get()
        self.app.config["auto_hide"] = val
        # Loại trừ tương hỗ: Nếu bật Tự làm mờ thì bắt buộc tắt Xuyên chuột để tránh xung đột compositing
        if val and self.app.config.get("click_through", False):
            self.app.config["click_through"] = False
            self.app.apply_click_through(False)
        self.app.save_config()
        if not val:
            self.app.root.attributes("-alpha", self.app.config.get("opacity", 0.90))

    def _toggle_quote_setting(self):
        val = self.var_quote.get()
        self.app.config["show_quote"] = val
        self.app.update_quote_visibility()
        self.app.save_config()

    def _toggle_water_setting(self):
        val = self.var_water.get()
        self.app.config.setdefault("water_reminder", {})["enabled"] = val
        self.app.save_config()

    def _toggle_progress_setting(self):
        val = self.var_progress.get()
        self.app.config["show_progress"] = val
        self.app.save_config()

    def _toggle_sound_setting(self):
        val = self.var_sound.get()
        self.app.config["sound_enabled"] = val
        sound_mgr.sound_enabled = val
        self.app.save_config()
