"""
Main Floating Clock Window UI and Core Event Loops
"""
from datetime import datetime, timedelta
import math
import sys
import time
import tkinter as tk
from tkinter import colorchooser, ttk

from app.config import load_config, save_config
from app.core.salary_calculator import calculate_salary_info, get_payday_countdown_info
from app.core.system_monitor import get_cpu_usage_percent, get_ram_usage_percent
from app.core.win32_utils import GlobalHotkeyManager, set_click_through
from app.services.ai_service import AIManager
from app.services.sound_service import FocusSoundManager, sound_mgr
from app.services.weather_service import WeatherManager
from app.ui.context_menu import ContextMenuBuilder
from app.ui.dialogs.alert_dialog import AlertNotificationDialog
from app.ui.dialogs.control_center import ControlCenterDialog
from app.ui.dialogs.hydration_dialog import HydrationReminderDialog
from app.ui.dialogs.task_dialog import QuickTaskDialog
from app.ui.dialogs.weather_dialog import WeatherForecastDialog


class FloatingClock:
    def __init__(self, root):
        self.root = root
        self.config = load_config()

        sound_mgr.sound_enabled = self.config.get("sound_enabled", True)
        self.weather_mgr = WeatherManager(self.config)
        self.focus_sound_mgr = FocusSoundManager(self.config)
        self.ai_mgr = AIManager(self.config)

        # Global Hotkey Manager (Fix F8 click-through lock)
        self.hotkey_mgr = GlobalHotkeyManager(on_f8_pressed=lambda: self.root.after(0, self.toggle_click_through))
        self.hotkey_mgr.start()

        self.current_mode = self.config.get("mode", "clock")
        self.timer_duration = self.config.get("timer_duration", 300)
        self.timer_remaining = self.config.get("timer_remaining", 300)
        self.timer_state = self.config.get("timer_state", "stopped")
        self.timer_last_tick = time.time()

        # Stopwatch State
        self.stopwatch_running = False
        self.stopwatch_start_time = 0.0
        self.stopwatch_elapsed = 0.0
        self.stopwatch_laps = []
        self.stopwatch_last_lap_time = 0.0

        # Pomodoro State
        self.pomo_running = False
        self.pomo_stage = "work"
        self.pomo_remaining = self.config.get("pomo_work_min", 25) * 60
        self.pomo_last_tick = time.time()
        self.pomo_cycle_count = 0

        self.last_water_remind_time = time.time()
        self.last_alarm_checked_min = -1
        self.last_quote_update_time = time.time()
        self.current_quote = self.ai_mgr.get_offline_quote("morning")

        self.drag_start_x = 0
        self.drag_start_y = 0
        self.drag_moved = False
        self.alert_dialog = None
        self.flash_step = 0

        self._last_rendered_text = ""
        self._last_sublabel_text = ""
        self._last_quote_rendered = ""
        self._last_sd_rendered = ""
        self._last_sm_rendered = ""
        self._last_task_rendered = ""
        self._last_sys_rendered = ""
        self._last_weather_rendered = ""
        self._last_snd_rendered = ""

        # Performance throttles
        self._last_sec_rendered = -1
        self._cached_salary_info = {}

        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", self.config.get("opacity", 0.90))
        self.root.configure(bg=self.config.get("border_color", "#2a3447"))

        self._build_ui()
        self.setup_bindings()
        self.adjust_size_and_position(initial=True)

        if self.config.get("click_through", False):
            self.apply_click_through(True)

        # First weather fetch
        if self.config.get("weather", {}).get("enabled", True):
            self.refresh_weather()

        self.update_loop()

    def save_config(self):
        try:
            self.config["x"] = self.root.winfo_x()
            self.config["y"] = self.root.winfo_y()
            self.config["mode"] = self.current_mode
            self.config["timer_duration"] = self.timer_duration
            self.config["timer_remaining"] = self.timer_remaining
            self.config["timer_state"] = self.timer_state
            save_config(self.config)
        except Exception:
            pass

    def get_today_departure_info(self, now):
        work_cfg = self.config.get("work_departure", {
            "start_time": "08:30",
            "mon_fri_time": "17:45",
            "sat_time": "16:00",
            "auto_schedule": True
        })
        weekday = now.weekday()
        vn_days = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ Nhật"]
        tag = vn_days[weekday]
        if weekday == 5:
            dep_time = work_cfg.get("sat_time", "16:00") + ":00"
        else:
            dep_time = work_cfg.get("mon_fri_time", "17:45") + ":00"
        return dep_time, tag

    def calculate_workday_progress(self, now):
        work_cfg = self.config.get("work_departure", {})
        start_str = work_cfg.get("start_time", "08:30")
        dep_time, _ = self.get_today_departure_info(now)
        try:
            today_str = now.strftime("%Y-%m-%d")
            dt_start = datetime.strptime(f"{today_str} {start_str}:00", "%Y-%m-%d %H:%M:%S")
            dt_end = datetime.strptime(f"{today_str} {dep_time}", "%Y-%m-%d %H:%M:%S")
            total_sec = (dt_end - dt_start).total_seconds()
            if total_sec <= 0:
                return 0.0, 0, 0
            if now < dt_start:
                return 0.0, total_sec, 0
            elif now > dt_end:
                return 100.0, total_sec, total_sec
            else:
                elapsed = (now - dt_start).total_seconds()
                pct = max(0.0, min(100.0, (elapsed / total_sec) * 100.0))
                return pct, total_sec, elapsed
        except Exception:
            return 0.0, 0, 0

    def get_current_context_tag(self, now):
        weekday = now.weekday()
        hour = now.hour
        minute = now.minute

        if weekday == 4 and hour >= 14:
            return "friday"
        if weekday == 5:
            return "saturday"
        if 16 <= hour < 18:
            return "leaving_soon"
        if 11 <= hour < 13:
            return "lunch"
        if 6 <= hour < 11:
            return "morning"
        if 13 <= hour < 16:
            return "afternoon"
        return "night"

    def request_next_quote(self):
        now = datetime.now()
        ctx = self.get_current_context_tag(now)

        def _on_quote_received(quote, is_ai, error):
            if quote:
                self.current_quote = quote
                self.last_quote_update_time = time.time()
                if self.config.get("show_quote", True):
                    self.quote_label.configure(text=quote)
                self._check_and_resize(self.time_label.cget("text"), self.sub_label.cget("text"))

        self.ai_mgr.fetch_ai_quote(ctx, callback=_on_quote_received, dispatcher=self.root.after_idle)

    def get_dynamic_color_by_seconds(self, remaining_sec, is_elapsed=False):
        if not self.config.get("dynamic_time_color", True):
            return self.config.get("text_color", "#00FFCC")

        hrs = max(0.0, float(remaining_sec) / 3600.0)
        if hrs >= 8.0:
            return "#EF4444"
        elif hrs >= 5.0:
            return "#F97316"
        elif hrs >= 2.0:
            return "#FBBF24"
        elif hrs >= 1.0:
            return "#10B981"
        else:
            return "#FFFFFF"

    def calculate_salary_info(self, now):
        return calculate_salary_info(now, self.config, self.get_today_departure_info)

    def toggle_salary_hide(self):
        self.config.setdefault("salary", {})
        self.config["salary"]["hidden"] = not self.config["salary"].get("hidden", False)
        self.save_config()

    def open_quick_task_dialog(self):
        QuickTaskDialog(self)

    def toggle_autohide(self):
        self.config["auto_hide"] = not self.config.get("auto_hide", False)
        self.save_config()
        if not self.config["auto_hide"]:
            self.root.attributes("-alpha", self.config.get("opacity", 0.90))

    def on_mouse_enter(self, event):
        if self.config.get("auto_hide", False):
            self.root.attributes("-alpha", self.config.get("opacity", 0.90))

    def on_mouse_leave(self, event):
        if self.config.get("auto_hide", False):
            self.root.attributes("-alpha", max(0.22, self.config.get("opacity", 0.90) * 0.35))

    def toggle_mini_mode(self):
        self.config["mini_mode"] = not self.config.get("mini_mode", False)
        self.apply_mini_mode()
        self.save_config()

    def toggle_dynamic_color(self):
        self.config["dynamic_time_color"] = not self.config.get("dynamic_time_color", True)
        self.save_config()

    def apply_mini_mode(self):
        is_mini = self.config.get("mini_mode", False)
        if is_mini:
            self.sub_label.pack_forget()
            self.date_label.pack_forget()
            self.quote_label.pack_forget()
            self.salary_daily_label.pack_forget()
            self.salary_month_label.pack_forget()
            self.task_label.pack_forget()
            self.sys_info_label.pack_forget()
            self.weather_label.pack_forget()
            self.sound_status_label.pack_forget()
            self.frame.configure(padx=10, pady=2)
        else:
            self.frame.configure(padx=16, pady=4)
            if self.config.get("show_sublabel", True):
                self.sub_label.pack(anchor="center", pady=(0, 1), before=self.time_label)
            if self.config.get("show_date", True) and self.current_mode == "clock":
                self.date_label.pack(anchor="center", pady=(1, 0))
            if self.config.get("show_quote", True):
                self.quote_label.pack(anchor="center", pady=(2, 0))
            self.update_extra_info_visibility()

    def _build_ui(self):
        self.frame = tk.Frame(
            self.root,
            bg=self.config.get("bg_color", "#0f131a"),
            padx=16,
            pady=4,
            highlightbackground=self.config.get("border_color", "#2a3447"),
            highlightthickness=1
        )
        self.frame.pack(fill="both", expand=True)

        self.sub_label = tk.Label(
            self.frame,
            text="",
            font=("Segoe UI", 8, "bold"),
            bg=self.config.get("bg_color", "#0f131a"),
            fg="#94A3B8"
        )
        if self.config.get("show_sublabel", True) and not self.config.get("mini_mode", False):
            self.sub_label.pack(anchor="center", pady=(0, 1))

        self.time_label = tk.Label(
            self.frame,
            text="00:00:00",
            font=("Consolas", self.config.get("font_size", 20), "bold"),
            bg=self.config.get("bg_color", "#0f131a"),
            fg=self.config.get("text_color", "#00FFCC")
        )
        self.time_label.pack(anchor="center")

        self.date_label = tk.Label(
            self.frame,
            text="",
            font=("Segoe UI", 8),
            bg=self.config.get("bg_color", "#0f131a"),
            fg="#64748B"
        )
        if self.config.get("show_date", True) and not self.config.get("mini_mode", False):
            self.date_label.pack(anchor="center", pady=(1, 0))

        self.quote_label = tk.Label(
            self.frame,
            text=self.current_quote,
            font=("Segoe UI", 8, "italic"),
            bg=self.config.get("bg_color", "#0f131a"),
            fg="#FCD34D",
            cursor="hand2"
        )
        if self.config.get("show_quote", True) and not self.config.get("mini_mode", False):
            self.quote_label.pack(anchor="center", pady=(2, 0))

        self.salary_daily_label = tk.Label(
            self.frame,
            text="",
            font=("Consolas", 8, "bold"),
            bg=self.config.get("bg_color", "#0f131a"),
            fg="#34D399"
        )

        self.salary_month_label = tk.Label(
            self.frame,
            text="",
            font=("Consolas", 8, "bold"),
            bg=self.config.get("bg_color", "#0f131a"),
            fg="#38BDF8"
        )

        self.task_label = tk.Label(
            self.frame,
            text="",
            font=("Segoe UI", 8, "bold"),
            bg=self.config.get("bg_color", "#0f131a"),
            fg="#F472B6"
        )

        self.sys_info_label = tk.Label(
            self.frame,
            text="",
            font=("Consolas", 8),
            bg=self.config.get("bg_color", "#0f131a"),
            fg="#94A3B8"
        )

        self.weather_label = tk.Label(
            self.frame,
            text="",
            font=("Segoe UI", 8),
            bg=self.config.get("bg_color", "#0f131a"),
            fg="#38BDF8"
        )

        self.sound_status_label = tk.Label(
            self.frame,
            text="",
            font=("Segoe UI", 8, "italic"),
            bg=self.config.get("bg_color", "#0f131a"),
            fg="#A78BFA"
        )

        self.update_extra_info_visibility()

    def update_date_visibility(self):
        if self.config.get("mini_mode", False):
            self.date_label.pack_forget()
            return
        if self.config.get("show_date", True) and self.current_mode == "clock":
            self.date_label.pack(anchor="center", pady=(1, 0))
        else:
            self.date_label.pack_forget()

    def update_quote_visibility(self):
        if self.config.get("mini_mode", False):
            self.quote_label.pack_forget()
            return
        if self.config.get("show_quote", True):
            self.quote_label.pack(anchor="center", pady=(2, 0))
        else:
            self.quote_label.pack_forget()

    def update_sublabel_visibility(self):
        if self.config.get("mini_mode", False):
            self.sub_label.pack_forget()
            return
        if self.config.get("show_sublabel", True):
            self.sub_label.pack(anchor="center", pady=(0, 1), before=self.time_label)
        else:
            self.sub_label.pack_forget()

    def toggle_focus_sound(self):
        st = self.config.get("focus_sound", {}).get("sound_type", "rain")
        self.focus_sound_mgr.toggle(st)
        self.update_extra_info_visibility()

    def select_and_play_sound(self, sound_type):
        self.config.setdefault("focus_sound", {})["sound_type"] = sound_type
        self.config["focus_sound"]["enabled"] = True
        self.save_config()
        self.focus_sound_mgr.play(sound_type)
        self.update_extra_info_visibility()

    def refresh_weather(self):
        self.weather_mgr.fetch_weather(
            callback=lambda txt, data: self.update_extra_info_visibility(),
            dispatcher=self.root.after_idle
        )

    def update_extra_info_visibility(self):
        if self.config.get("mini_mode", False):
            self.salary_daily_label.pack_forget()
            self.salary_month_label.pack_forget()
            self.task_label.pack_forget()
            self.sys_info_label.pack_forget()
            self.weather_label.pack_forget()
            self.sound_status_label.pack_forget()
            return

        sal_cfg = self.config.get("salary", {})
        sal_on = sal_cfg.get("enabled", False)
        if sal_on and sal_cfg.get("show_daily", True):
            self.salary_daily_label.pack(anchor="center", pady=(2, 0))
        else:
            self.salary_daily_label.pack_forget()

        if sal_on and sal_cfg.get("show_monthly", True):
            self.salary_month_label.pack(anchor="center", pady=(1, 0))
        else:
            self.salary_month_label.pack_forget()

        if self.config.get("focus_task", {}).get("enabled", False) and self.config.get("focus_task", {}).get("text", ""):
            self.task_label.pack(anchor="center", pady=(2, 0))
        else:
            self.task_label.pack_forget()

        if self.config.get("show_sys_monitor", False):
            self.sys_info_label.pack(anchor="center", pady=(1, 0))
        else:
            self.sys_info_label.pack_forget()

        if self.config.get("weather", {}).get("enabled", True) and self.weather_mgr.current_weather_str:
            self.weather_label.configure(text=self.weather_mgr.current_weather_str)
            self.weather_label.pack(anchor="center", pady=(1, 0))
        else:
            self.weather_label.pack_forget()

        if self.focus_sound_mgr.is_playing:
            snd_info = self.focus_sound_mgr.SOUND_TYPES.get(self.focus_sound_mgr.current_sound, {})
            icon = snd_info.get("icon", "🎧")
            self.sound_status_label.configure(text=f"Playing: {icon} {snd_info.get('name', '')}")
            self.sound_status_label.pack(anchor="center", pady=(1, 0))
        else:
            self.sound_status_label.pack_forget()

        self.adjust_size_and_position(initial=False)

    def setup_bindings(self):
        widgets = (self.root, self.frame, self.time_label, self.sub_label, self.date_label,
                   self.salary_daily_label, self.salary_month_label, self.task_label,
                   self.sys_info_label, self.weather_label, self.sound_status_label)
        for w in widgets:
            w.bind("<ButtonPress-1>", self.start_drag)
            w.bind("<B1-Motion>", self.do_drag)
            w.bind("<ButtonRelease-1>", self.stop_drag)
            w.bind("<Button-3>", self.show_context_menu)
            w.bind("<Double-Button-1>", self.on_double_click)

        # Quote label: allow drag, but if clicked without moving, fetch next quote
        self.quote_label.bind("<ButtonPress-1>", self.start_drag)
        self.quote_label.bind("<B1-Motion>", self.do_drag)
        self.quote_label.bind("<ButtonRelease-1>", self._on_quote_release)
        self.quote_label.bind("<Button-3>", self.show_context_menu)

        # Auto-hide bindings
        self.root.bind("<Enter>", self.on_mouse_enter)
        self.root.bind("<Leave>", self.on_mouse_leave)

        # Keyboard shortcuts
        self.root.bind("<F8>", lambda e: self.toggle_click_through())
        self.root.bind("<F2>", lambda e: self.cycle_next_mode())
        self.root.bind("<F9>", lambda e: self.toggle_focus_sound())
        self.root.bind("<m>", lambda e: self.toggle_mini_mode())
        self.root.bind("<M>", lambda e: self.toggle_mini_mode())
        self.root.bind("<d>", lambda e: self.toggle_dynamic_color())
        self.root.bind("<D>", lambda e: self.toggle_dynamic_color())
        self.root.bind("<s>", lambda e: self.toggle_salary_hide())
        self.root.bind("<S>", lambda e: self.toggle_salary_hide())
        self.root.bind("<t>", lambda e: self.open_quick_task_dialog())
        self.root.bind("<T>", lambda e: self.open_quick_task_dialog())
        self.root.bind("<w>", lambda e: WeatherForecastDialog(self))
        self.root.bind("<W>", lambda e: WeatherForecastDialog(self))
        self.root.bind("<h>", lambda e: self.toggle_autohide())
        self.root.bind("<H>", lambda e: self.toggle_autohide())
        self.root.bind("<space>", lambda e: self.on_space_key())

    def _on_quote_release(self, event):
        self.stop_drag(event)
        if not self.drag_moved:
            self.request_next_quote()

    def start_drag(self, event):
        if not self.config["locked"]:
            self.drag_start_x = event.x_root - self.root.winfo_x()
            self.drag_start_y = event.y_root - self.root.winfo_y()
            self.drag_moved = False

    def do_drag(self, event):
        if not self.config["locked"]:
            self.drag_moved = True
            x = event.x_root - self.drag_start_x
            y = event.y_root - self.drag_start_y
            # Multi-monitor drag fix: Allow moving across negative & extra display bounds
            # Keep at least a small portion on screen
            self.root.geometry(f"+{x}+{y}")

    def stop_drag(self, event):
        self.save_config()

    def on_double_click(self, event):
        if self.current_mode == "timer":
            if self.timer_state == "running":
                self.pause_timer()
            else:
                self.start_timer()
        elif self.current_mode == "stopwatch":
            if self.stopwatch_running:
                self.pause_stopwatch()
            else:
                self.start_stopwatch()
        elif self.current_mode == "pomodoro":
            self.pomo_running = not self.pomo_running
        else:
            self.toggle_mini_mode()

    def on_space_key(self):
        if self.current_mode == "timer":
            if self.timer_state == "running":
                self.pause_timer()
            else:
                self.start_timer()
        elif self.current_mode == "stopwatch":
            if self.stopwatch_running:
                self.pause_stopwatch()
            else:
                self.start_stopwatch()

    def show_context_menu(self, event):
        menu = ContextMenuBuilder.build(self)
        menu.tk_popup(event.x_root, event.y_root)

    def open_control_center(self):
        ControlCenterDialog(self)

    def activate_today_departure(self):
        now = datetime.now()
        today_dep, today_tag = self.get_today_departure_info(now)
        self.config["target_time_str"] = today_dep
        self.config["target_time_label"] = f"Tan làm ({today_tag})"
        self.config["target_time_active"] = True
        self.switch_mode("target_time")
        self.save_config()

    def switch_mode(self, mode_name):
        self.current_mode = mode_name
        self.config["mode"] = mode_name
        self.update_date_visibility()
        self.update_sublabel_visibility()
        self.save_config()

    def cycle_next_mode(self):
        mode_order = ["clock", "target_time", "timer", "stopwatch", "pomodoro"]
        try:
            curr_idx = mode_order.index(self.current_mode)
            next_mode = mode_order[(curr_idx + 1) % len(mode_order)]
        except ValueError:
            next_mode = "clock"
        self.switch_mode(next_mode)

    def start_quick_timer(self, duration_sec):
        self.set_timer_seconds(duration_sec)
        self.switch_mode("timer")
        self.start_timer()

    def set_timer_seconds(self, duration_sec):
        self.timer_duration = duration_sec
        self.timer_remaining = duration_sec
        self.timer_state = "stopped"
        self.save_config()

    def add_timer_seconds(self, delta_sec):
        self.timer_remaining = max(0, self.timer_remaining + delta_sec)
        self.timer_duration = max(self.timer_remaining, self.timer_duration)
        self.save_config()

    def start_timer(self):
        self.timer_state = "running"
        self.timer_last_tick = time.time()
        if self.alert_dialog and self.alert_dialog.winfo_exists():
            try:
                self.alert_dialog.destroy()
            except Exception:
                pass
        self.save_config()

    def pause_timer(self):
        self.timer_state = "paused"
        self.save_config()

    def reset_timer(self):
        self.timer_state = "stopped"
        self.timer_remaining = self.timer_duration
        self.save_config()

    def trigger_timer_finished(self):
        self.timer_state = "stopped"
        sound_mgr.play_alarm_loop("Hết giờ đếm ngược!")

        if self.alert_dialog and self.alert_dialog.winfo_exists():
            try:
                self.alert_dialog.destroy()
            except Exception:
                pass

        self.alert_dialog = AlertNotificationDialog(
            self.root,
            "⏳ Hết giờ đếm ngược!",
            "⏳ ĐÃ HẾT GIỜ ĐẾM NGƯỢC!",
            on_dismiss=lambda: None,
            on_restart=lambda: self.start_timer()
        )

    # ---------------- ⏱️ STOPWATCH LOGIC ----------------
    def start_stopwatch(self):
        self.stopwatch_running = True
        self.stopwatch_start_time = time.time() - self.stopwatch_elapsed

    def pause_stopwatch(self):
        if self.stopwatch_running:
            self.stopwatch_elapsed = time.time() - self.stopwatch_start_time
            self.stopwatch_running = False

    def reset_stopwatch(self):
        self.stopwatch_running = False
        self.stopwatch_elapsed = 0.0
        self.stopwatch_laps.clear()
        self.stopwatch_last_lap_time = 0.0

    def lap_stopwatch(self):
        if not self.stopwatch_running and self.stopwatch_elapsed == 0.0:
            return
        cur_total = (time.time() - self.stopwatch_start_time) if self.stopwatch_running else self.stopwatch_elapsed
        lap_time = cur_total - self.stopwatch_last_lap_time
        self.stopwatch_last_lap_time = cur_total

        total_str = self._format_stopwatch_str(cur_total)
        lap_str = self._format_stopwatch_str(lap_time)
        self.stopwatch_laps.append({
            "lap_time": lap_time,
            "total_time": cur_total,
            "lap_str": lap_str,
            "total_str": total_str
        })

    def _format_stopwatch_str(self, sec):
        m = int(sec // 60)
        s = int(sec % 60)
        cs = int((sec - int(sec)) * 100)
        if m >= 60:
            h = m // 60
            m = m % 60
            return f"{h:02d}:{m:02d}:{s:02d}.{cs:02d}"
        else:
            return f"{m:02d}:{s:02d}.{cs:02d}"

    # ---------------- 🍅 POMODORO LOGIC ----------------
    def start_pomodoro_work(self):
        self.pomo_stage = "work"
        self.pomo_remaining = self.config.get("pomo_work_min", 25) * 60
        self.pomo_running = True

    def start_pomodoro_break(self, is_long=False):
        if is_long:
            self.pomo_stage = "long_break"
            self.pomo_remaining = self.config.get("pomo_long_break_min", 15) * 60
        else:
            self.pomo_stage = "break"
            self.pomo_remaining = self.config.get("pomo_break_min", 5) * 60
        self.pomo_running = True

    def trigger_pomodoro_stage_complete(self):
        self.pomo_running = False
        if self.pomo_stage == "work":
            self.pomo_cycle_count += 1
            sound_mgr.play_pomo_break()
            if self.pomo_cycle_count % self.config.get("pomo_cycles", 4) == 0:
                msg = f"🍅 Hoàn thành phiên #{self.pomo_cycle_count}! Đến lúc NGHỈ DÀI 15 phút rồi."
                is_long = True
            else:
                msg = f"🍅 Hoàn thành tập trung! Đến lúc NGHỈ NGẮN 5 phút thư giãn."
                is_long = False

            AlertNotificationDialog(
                self.root,
                "🍅 Pomodoro - Giờ nghỉ ngơi",
                msg,
                on_dismiss=lambda: self.start_pomodoro_break(is_long)
            )
        else:
            sound_mgr.play_pomo_break()
            msg = "⚡ Hết giờ nghỉ! Bạn đã sẵn sàng cho phiên tập trung tiếp theo chưa?"
            AlertNotificationDialog(
                self.root,
                "🍅 Pomodoro - Bắt đầu làm việc",
                msg,
                on_dismiss=lambda: self.start_pomodoro_work()
            )

    # ---------------- ⏰ ALARMS CHECKER ----------------
    def check_alarms(self, now):
        cur_hm = now.strftime("%H:%M")
        cur_min_val = now.minute

        if cur_min_val == self.last_alarm_checked_min:
            return
        self.last_alarm_checked_min = cur_min_val

        alarms = self.config.get("alarms", [])
        for idx, alm in enumerate(alarms):
            if alm.get("enabled", False) and alm.get("time") == cur_hm:
                self.trigger_alarm_alert(alm)
                if not alm.get("repeat", True):
                    alm["enabled"] = False
                    self.save_config()

    def trigger_alarm_alert(self, alm):
        sound_mgr.play_alarm_loop(alm.get("label", "Báo thức"))

        label_txt = alm.get("label", "Báo thức")
        time_txt = alm.get("time", "")

        def snooze_action():
            snooze_dt = datetime.now() + timedelta(minutes=5)
            snooze_time = snooze_dt.strftime("%H:%M")
            self.config.setdefault("alarms", []).append({
                "id": int(time.time()),
                "time": snooze_time,
                "label": f"(Báo lại 5p) {label_txt}",
                "enabled": True,
                "repeat": False
            })
            self.save_config()

        AlertNotificationDialog(
            self.root,
            f"⏰ Báo thức: {time_txt}",
            f"⏰ ĐÃ ĐẾN GIỜ BÁO THỨC!\n\n[{time_txt}] {label_txt}",
            on_dismiss=lambda: None,
            on_snooze=snooze_action
        )

    # ---------------- 💧 WATER REMINDER CHECKER ----------------
    def check_water_reminder(self):
        w_cfg = self.config.get("water_reminder", {"enabled": True, "interval_min": 45})
        if not w_cfg.get("enabled", True):
            return

        interval_sec = w_cfg.get("interval_min", 45) * 60
        if time.time() - self.last_water_remind_time >= interval_sec:
            self.last_water_remind_time = time.time()
            sound_mgr.play_water_chime()
            try:
                HydrationReminderDialog(self.root)
            except Exception:
                pass

    # ---------------- 🎯 TARGET TIME CHECKER ----------------
    def check_target_time(self, now):
        if not self.config.get("target_time_active", False):
            return
        tgt_str = self.config.get("target_time_str", "17:45:00")
        try:
            today_str = now.strftime("%Y-%m-%d")
            tgt_dt = datetime.strptime(f"{today_str} {tgt_str}", "%Y-%m-%d %H:%M:%S")
            diff = (tgt_dt - now).total_seconds()
            if -2 <= diff <= 1:
                self.config["target_time_active"] = False
                self.save_config()
                sound_mgr.play_alarm_loop("Đã đến giờ mục tiêu!")
                lbl = self.config.get("target_time_label", "Tan làm")
                AlertNotificationDialog(
                    self.root,
                    f"🎯 Đã đến mốc giờ: {tgt_str[:5]}",
                    f"🎯 ĐÃ ĐẾN MỐC THỜI GIAN: {tgt_str[:5]}\n\n🎉 {lbl} 🎉\nChúc fen buổi chiều/tối tràn ngập niềm vui!",
                    on_dismiss=lambda: None
                )
        except Exception:
            pass

    # ---------------- 🔄 MASTER UPDATE LOOP ----------------
    def update_loop(self):
        try:
            now = datetime.now()
            cur_sec = int(now.timestamp())

            self.check_alarms(now)
            self.check_target_time(now)
            self.check_water_reminder()

            # Rotate quote every 45s
            if time.time() - self.last_quote_update_time > 45:
                self.request_next_quote()

            # Weather update check (every 30m by default)
            w_cfg = self.config.get("weather", {})
            if w_cfg.get("enabled", True):
                w_interval = max(5, w_cfg.get("auto_refresh_min", 30)) * 60
                if time.time() - getattr(self, "_last_weather_check", 0) > w_interval:
                    self._last_weather_check = time.time()
                    self.refresh_weather()

            # Render extra info (Salary ticker & Focus task throttled to 1s)
            if not self.config.get("mini_mode", False):
                if cur_sec != self._last_sec_rendered:
                    self._last_sec_rendered = cur_sec
                    sal_cfg = self.config.get("salary", {})
                    if sal_cfg.get("enabled", False):
                        s_info = self.calculate_salary_info(now)
                        if s_info.get("show_daily", True):
                            self.salary_daily_label.configure(text=s_info["daily_str"])
                        if s_info.get("show_monthly", True):
                            self.salary_month_label.configure(text=s_info["month_str"])

                    if self.config.get("focus_task", {}).get("enabled", False):
                        t_txt = self.config.get("focus_task", {}).get("text", "")
                        if t_txt:
                            display_t = (t_txt[:30] + "...") if len(t_txt) > 33 else t_txt
                            self.task_label.configure(text=f"🎯 {display_t}")

                    # Realtime Win32 CPU & RAM monitor
                    if self.config.get("show_sys_monitor", False):
                        cpu_val = get_cpu_usage_percent()
                        ram_val = get_ram_usage_percent()
                        self.sys_info_label.configure(text=f"⚡ CPU: {cpu_val}%  •  RAM: {ram_val}%")

            mascot = self.config.get("mascot", "🚀")
            mascot_prefix = f"{mascot} " if mascot else ""

            if self.current_mode == "clock":
                self._render_clock_mode(now, mascot_prefix)
            elif self.current_mode == "timer":
                self._render_timer_mode(mascot_prefix)
            elif self.current_mode == "target_time":
                self._render_target_time_mode(now, mascot_prefix)
            elif self.current_mode == "stopwatch":
                self._render_stopwatch_mode(mascot_prefix)
            elif self.current_mode == "pomodoro":
                self._render_pomodoro_mode(mascot_prefix)

            if sound_mgr.is_ringing():
                self.flash_step += 1
                fl_color = "#EF4444" if self.flash_step % 2 == 0 else "#F59E0B"
                self.frame.configure(highlightbackground=fl_color, highlightthickness=2)
            else:
                self.frame.configure(highlightbackground=self.config.get("border_color", "#2a3447"), highlightthickness=1)
        except Exception:
            pass
        finally:
            self.root.after(50, self.update_loop)

    def _render_clock_mode(self, now, mascot_prefix):
        show_sec = self.config.get("show_seconds", True)
        show_ms = self.config.get("show_ms", False)
        is_12h = self.config.get("time_format_12h", False)

        if is_12h:
            fmt = "%I:%M:%S %p" if show_sec else "%I:%M %p"
        else:
            fmt = "%H:%M:%S" if show_sec else "%H:%M"

        time_str = now.strftime(fmt)
        if show_ms:
            ms = int(now.microsecond / 10000)
            time_str += f".{ms:02d}"

        if self.config.get("dynamic_time_color", True):
            try:
                work_cfg = self.config.get("work_departure", {})
                today_dep, _ = self.get_today_departure_info(now)
                today_str = now.strftime("%Y-%m-%d")
                dt_dep = datetime.strptime(f"{today_str} {today_dep}", "%Y-%m-%d %H:%M:%S")
                rem_sec = (dt_dep - now).total_seconds()
                fg_col = self.get_dynamic_color_by_seconds(rem_sec)
            except Exception:
                fg_col = self.config.get("text_color", "#00FFCC")
        else:
            fg_col = self.config.get("text_color", "#00FFCC")

        self.time_label.configure(text=time_str, fg=fg_col)

        active_alarms = [a for a in self.config.get("alarms", []) if a.get("enabled", False)]
        if active_alarms:
            next_alm = sorted(active_alarms, key=lambda x: x.get("time", ""))[0]
            sub_txt = f"{mascot_prefix}🕒 CLOCK  •  ⏰ {next_alm.get('time', '')}"
        else:
            sub_txt = f"{mascot_prefix}🕒 CLOCK"

        self.sub_label.configure(text=sub_txt, fg="#94A3B8")

        if self.config.get("show_date", True) and not self.config.get("mini_mode", False):
            vn_days = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ Nhật"]
            date_str = f"{vn_days[now.weekday()]}, {now.strftime('%d/%m/%Y')}"
            self.date_label.configure(text=date_str)

        self._check_and_resize(time_str, sub_txt)

    def _render_timer_mode(self, mascot_prefix):
        now_ts = time.time()
        if self.timer_state == "running":
            delta = now_ts - self.timer_last_tick
            self.timer_last_tick = now_ts
            self.timer_remaining -= delta
            if self.timer_remaining <= 0:
                self.timer_remaining = 0
                self.trigger_timer_finished()

        rem = max(0, int(math.ceil(self.timer_remaining)))
        h = rem // 3600
        m = (rem % 3600) // 60
        s = rem % 60
        time_str = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"

        if self.timer_state == "running":
            state_icon = "▶"
            fg_col = self.get_dynamic_color_by_seconds(self.timer_remaining) if self.config.get("dynamic_time_color", True) else self.config.get("text_color", "#00FFCC")
        elif self.timer_state == "paused":
            state_icon = "⏸"
            fg_col = "#F59E0B"
        else:
            state_icon = "⏹"
            fg_col = "#94A3B8"

        self.time_label.configure(text=time_str, fg=fg_col)
        dur_m = self.timer_duration // 60
        sub_txt = f"{mascot_prefix}⏳ TIMER [{state_icon}] ({dur_m}m)"
        self.sub_label.configure(text=sub_txt, fg="#38BDF8")
        self._check_and_resize(time_str, sub_txt)

    def _render_target_time_mode(self, now, mascot_prefix):
        tgt_str = self.config.get("target_time_str", "17:45:00")
        lbl = self.config.get("target_time_label", "Tan làm")
        try:
            today_str = now.strftime("%Y-%m-%d")
            tgt_dt = datetime.strptime(f"{today_str} {tgt_str}", "%Y-%m-%d %H:%M:%S")
            diff = (tgt_dt - now).total_seconds()
            if diff <= 0:
                time_str = "🎉 00:00:00"
                fg_col = "#10B981"
                pct_str = " (100%)"
            else:
                rem = int(math.ceil(diff))
                h = rem // 3600
                m = (rem % 3600) // 60
                s = rem % 60
                time_str = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
                fg_col = self.get_dynamic_color_by_seconds(diff)
                pct, _, _ = self.calculate_workday_progress(now)
                pct_str = f" • {pct:.0f}%" if self.config.get("show_progress", True) else ""
        except Exception:
            time_str = "--:--"
            fg_col = self.config.get("text_color", "#00FFCC")
            pct_str = ""

        self.time_label.configure(text=time_str, fg=fg_col)
        sub_txt = f"{mascot_prefix}🎯 {lbl.upper()} ({tgt_str[:5]}){pct_str}"
        self.sub_label.configure(text=sub_txt, fg="#F59E0B")
        self._check_and_resize(time_str, sub_txt)

    def _render_stopwatch_mode(self, mascot_prefix):
        cur_total = (time.time() - self.stopwatch_start_time) if self.stopwatch_running else self.stopwatch_elapsed
        time_str = self._format_stopwatch_str(cur_total)
        st_icon = "▶" if self.stopwatch_running else ("⏸" if self.stopwatch_elapsed > 0 else "⏹")
        fg_col = "#10B981" if self.stopwatch_running else ("#F59E0B" if self.stopwatch_elapsed > 0 else "#94A3B8")

        self.time_label.configure(text=time_str, fg=fg_col)
        laps_cnt = len(self.stopwatch_laps)
        sub_txt = f"{mascot_prefix}⏱️ STOPWATCH [{st_icon}] (Laps: {laps_cnt})"
        self.sub_label.configure(text=sub_txt, fg="#10B981")
        self._check_and_resize(time_str, sub_txt)

    def _render_pomodoro_mode(self, mascot_prefix):
        now_ts = time.time()
        if self.pomo_running:
            delta = now_ts - self.pomo_last_tick
            self.pomo_last_tick = now_ts
            self.pomo_remaining -= delta
            if self.pomo_remaining <= 0:
                self.pomo_remaining = 0
                self.trigger_pomodoro_stage_complete()
        else:
            self.pomo_last_tick = now_ts

        rem = max(0, int(math.ceil(self.pomo_remaining)))
        m = rem // 60
        s = rem % 60
        time_str = f"{m:02d}:{s:02d}"

        if self.pomo_stage == "work":
            st_text = "FOCUS"
            fg_col = "#EF4444" if self.pomo_running else "#F87171"
            sub_col = "#EF4444"
        elif self.pomo_stage == "break":
            st_text = "SHORT BREAK"
            fg_col = "#10B981" if self.pomo_running else "#34D399"
            sub_col = "#10B981"
        else:
            st_text = "LONG BREAK"
            fg_col = "#38BDF8" if self.pomo_running else "#60A5FA"
            sub_col = "#38BDF8"

        st_icon = "▶" if self.pomo_running else "⏸"
        self.time_label.configure(text=time_str, fg=fg_col)
        sub_txt = f"{mascot_prefix}🍅 {st_text} #{self.pomo_cycle_count + 1} [{st_icon}]"
        self.sub_label.configure(text=sub_txt, fg=sub_col)
        self._check_and_resize(time_str, sub_txt)

    def _check_and_resize(self, time_str, sub_txt):
        quote_txt = self.current_quote if self.config.get("show_quote", True) else ""
        s_d_txt = self.salary_daily_label.cget("text") if not self.config.get("mini_mode", False) else ""
        s_m_txt = self.salary_month_label.cget("text") if not self.config.get("mini_mode", False) else ""
        task_txt = self.task_label.cget("text") if not self.config.get("mini_mode", False) else ""
        sys_txt = self.sys_info_label.cget("text") if (not self.config.get("mini_mode", False) and self.config.get("show_sys_monitor", False)) else ""
        weather_txt = self.weather_label.cget("text") if not self.config.get("mini_mode", False) else ""
        snd_txt = self.sound_status_label.cget("text") if not self.config.get("mini_mode", False) else ""

        if (len(time_str) != len(self._last_rendered_text) or
            sub_txt != self._last_sublabel_text or
            quote_txt != self._last_quote_rendered or
            len(s_d_txt) != len(getattr(self, "_last_sd_rendered", "")) or
            len(s_m_txt) != len(getattr(self, "_last_sm_rendered", "")) or
            task_txt != getattr(self, "_last_task_rendered", "") or
            len(sys_txt) != len(getattr(self, "_last_sys_rendered", "")) or
            weather_txt != getattr(self, "_last_weather_rendered", "") or
            snd_txt != getattr(self, "_last_snd_rendered", "")):
            self._last_rendered_text = time_str
            self._last_sublabel_text = sub_txt
            self._last_quote_rendered = quote_txt
            self._last_sd_rendered = s_d_txt
            self._last_sm_rendered = s_m_txt
            self._last_task_rendered = task_txt
            self._last_sys_rendered = sys_txt
            self._last_weather_rendered = weather_txt
            self._last_snd_rendered = snd_txt
            self.adjust_size_and_position(initial=False)

    def adjust_size_and_position(self, initial=False):
        self.root.update_idletasks()
        req_w = self.frame.winfo_reqwidth() + 12
        req_h = self.frame.winfo_reqheight() + 4
        screen_w = self.root.winfo_screenwidth()

        if initial:
            if self.config.get("x") is None:
                x = (screen_w - req_w) // 2
                y = self.config.get("y", 10)
            else:
                x = self.config["x"]
                y = self.config["y"]
        else:
            x = self.root.winfo_x()
            y = self.root.winfo_y()

        self.root.geometry(f"{req_w}x{req_h}+{x}+{y}")

    def set_text_color(self, color_hex):
        self.config["text_color"] = color_hex
        self.config["dynamic_time_color"] = False
        self.time_label.configure(fg=color_hex)
        self.save_config()

    def pick_custom_color(self):
        col = colorchooser.askcolor(color=self.config["text_color"], title="Chọn màu chữ")[1]
        if col:
            self.set_text_color(col)

    def set_opacity(self, opacity_float):
        self.config["opacity"] = opacity_float
        self.root.attributes("-alpha", opacity_float)
        self.save_config()

    def set_font_size(self, size_int):
        self.config["font_size"] = size_int
        self.time_label.configure(font=("Consolas", size_int, "bold"))
        self.adjust_size_and_position(initial=False)
        self.save_config()

    def toggle_lock(self):
        self.config["locked"] = not self.config["locked"]
        self.save_config()

    def toggle_click_through(self):
        self.config["click_through"] = not self.config["click_through"]
        self.apply_click_through(self.config["click_through"])
        self.save_config()

    def apply_click_through(self, enable):
        try:
            hwnd = self.root.winfo_id()
            set_click_through(hwnd, enable)
        except Exception:
            pass

    def reset_to_top_center(self):
        self.root.update_idletasks()
        w = self.frame.winfo_reqwidth() + 12
        h = self.frame.winfo_reqheight() + 4
        sw = self.root.winfo_screenwidth()
        self.config["x"] = (sw - w) // 2
        self.config["y"] = 10
        self.root.geometry(f"{w}x{h}+{self.config['x']}+{self.config['y']}")
        self.save_config()

    def reset_to_top_right(self):
        self.root.update_idletasks()
        w = self.frame.winfo_reqwidth() + 12
        h = self.frame.winfo_reqheight() + 4
        sw = self.root.winfo_screenwidth()
        self.config["x"] = sw - w - 20
        self.config["y"] = 10
        self.root.geometry(f"{w}x{h}+{self.config['x']}+{self.config['y']}")
        self.save_config()

    def reset_to_top_left(self):
        self.root.update_idletasks()
        w = self.frame.winfo_reqwidth() + 12
        h = self.frame.winfo_reqheight() + 4
        self.config["x"] = 20
        self.config["y"] = 10
        self.root.geometry(f"{w}x{h}+{self.config['x']}+{self.config['y']}")
        self.save_config()

    def reset_to_bottom_center(self):
        self.root.update_idletasks()
        w = self.frame.winfo_reqwidth() + 12
        h = self.frame.winfo_reqheight() + 4
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.config["x"] = (sw - w) // 2
        self.config["y"] = sh - h - 50
        self.root.geometry(f"{w}x{h}+{self.config['x']}+{self.config['y']}")
        self.save_config()

    def quit_app(self):
        try:
            self.hotkey_mgr.stop()
        except Exception:
            pass
        try:
            self.focus_sound_mgr.stop()
            sound_mgr.stop_alarm()
        except Exception:
            pass
        self.save_config()
        self.root.destroy()
        sys.exit(0)
