"""
Main Floating Clock Window UI and Core Event Loops
"""
from datetime import datetime, timedelta
import math
import os
import sys
import time
import tkinter as tk
from tkinter import colorchooser, ttk

from app.config import APP_DIR, BUNDLE_DIR, load_config, save_config
from app.constants import APP_VERSION
from app.core.autostart import is_start_with_windows, set_start_with_windows
from app.core.salary_calculator import calculate_salary_info, get_payday_countdown_info
from app.core.system_monitor import get_cpu_usage_percent, get_ram_usage_percent
from app.core.win32_utils import (
    GlobalHotkeyManager,
    force_topmost,
    get_virtual_screen_rect,
    hide_from_taskbar,
    is_click_through_active,
    is_window_visible_win32,
    set_click_through,
)
from app.services.ai_service import AIManager
from app.services.sound_service import FocusSoundManager, sound_mgr
from app.services.update_service import UpdateManager
from app.services.weather_service import WeatherManager
from app.ui.context_menu import ContextMenuBuilder
from app.ui.dialogs.alert_dialog import AlertNotificationDialog
from app.ui.dialogs.control_center import ControlCenterDialog
from app.ui.dialogs.hydration_dialog import HydrationReminderDialog
from app.ui.dialogs.task_dialog import QuickTaskDialog
from app.ui.dialogs.update_dialog import UpdateNotificationDialog
from app.ui.dialogs.weather_dialog import WeatherForecastDialog
from app.services.mascot_service import MascotManager
from app.messages import ALERT_MESSAGES
from tkinter import messagebox


class FloatingClock:
    def __init__(self, root):
        self.root = root
        self.config = load_config()

        sound_mgr.sound_enabled = self.config.get("sound_enabled", True)
        self.weather_mgr = WeatherManager(self.config)
        self.focus_sound_mgr = FocusSoundManager(self.config)
        self.ai_mgr = AIManager(self.config)
        self.mascot_mgr = MascotManager(self.root, self.config)
        self.update_mgr = UpdateManager(self.config)
        self._last_mascot_state = None

        # Global Hotkey Manager (Fix F8 click-through lock)
        # Debounce F8: tránh queue nhiều after() khi giữ/spam phím → config lệch với style thật
        self._click_through_toggle_ts = 0.0
        self._last_visibility_check = 0.0
        self.hotkey_mgr = GlobalHotkeyManager(on_f8_pressed=lambda: self.root.after(0, self._on_f8_hotkey))
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

        # Context Menu State & Ghost Window Prevention
        self._current_menu = None
        self._menu_anchor = None
        self._is_menu_open = False
        self._hydration_dialog = None

        # Thiết lập Icon cho ứng dụng
        icon_candidates = [
            os.path.join(BUNDLE_DIR, "icon.ico"),
            os.path.join(BUNDLE_DIR, "app", "assets", "icon.ico"),
            os.path.join(APP_DIR, "icon.ico"),
        ]
        for ipath in icon_candidates:
            if os.path.exists(ipath):
                try:
                    self.root.iconbitmap(ipath)
                    break
                except Exception:
                    pass

        # Tool window: không nút taskbar và không vào Alt+Tab.
        # Đặt trước overrideredirect để Tk tạo wrapper đúng kiểu.
        try:
            self.root.attributes("-toolwindow", True)
        except Exception:
            pass
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", self.config.get("opacity", 0.90))
        self.root.configure(bg=self.config.get("border_color", "#2a3447"))

        self._build_ui()
        self.setup_bindings()
        self.adjust_size_and_position(initial=True)

        # Đảm bảo auto_hide và click_through chỉ được bật 1 trong 2 (loại trừ lẫn nhau)
        if self.config.get("click_through", False) and self.config.get("auto_hide", False):
            self.config["auto_hide"] = False

        # Click-through lúc này cửa sổ còn withdraw — chỉ đánh dấu, apply thật sau khi map
        self._pending_click_through = bool(self.config.get("click_through", False))

        # First weather fetch
        if self.config.get("weather", {}).get("enabled", True):
            self.refresh_weather()

        self._is_closing = False
        try:
            self.root.protocol("WM_DELETE_WINDOW", self.quit_app)
        except Exception:
            pass

        self.update_loop()
        # Chạy sau deiconify ở main(): Win32 style bị Tk ghi đè lúc map cửa sổ.
        self.root.after(0, self._on_window_mapped)
        # auto_hide bật sẵn thì làm mờ ngay nếu chuột không nằm trên đồng hồ
        self.root.after(50, self._sync_autohide_alpha)

        # Tự động kiểm tra bản cập nhật ngầm sau khi app khởi động xong
        if self.config.get("check_updates_on_startup", True):
            self.root.after(4000, lambda: self.check_for_updates(interactive=False))

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

    @staticmethod
    def _normalize_time_str(time_str, default="00:00:00"):
        """Đảm bảo chuỗi giờ luôn chuẩn định dạng HH:MM:SS kể cả khi người dùng nhập HH:MM"""
        if not time_str:
            return default
        parts = str(time_str).strip().split(":")
        if len(parts) == 2:
            return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}:00"
        elif len(parts) == 3:
            return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}:{parts[2].zfill(2)}"
        return default

    def calculate_workday_progress(self, now):
        work_cfg = self.config.get("work_departure", {})
        start_str = work_cfg.get("start_time", "08:30")
        dep_time, _ = self.get_today_departure_info(now)
        try:
            today_str = now.strftime("%Y-%m-%d")
            norm_start = self._normalize_time_str(start_str, "08:30:00")
            norm_dep = self._normalize_time_str(dep_time, "17:45:00")
            dt_start = datetime.strptime(f"{today_str} {norm_start}", "%Y-%m-%d %H:%M:%S")
            dt_end = datetime.strptime(f"{today_str} {norm_dep}", "%Y-%m-%d %H:%M:%S")
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
        now_ts = time.time()
        # Chống spam gọi API AI liên tục khi click nhanh hoặc double-click
        if now_ts - getattr(self, "_last_quote_request_ts", 0) < 1.0:
            return
        self._last_quote_request_ts = now_ts

        now = datetime.now()
        ctx = self.get_current_context_tag(now)

        def _on_quote_received(quote, is_ai, error):
            if quote:
                self.current_quote = quote
                self.last_quote_update_time = time.time()
                if self.config.get("show_quote", True):
                    self.quote_label.configure(text=quote)
                self._check_and_resize(self.time_label.cget("text"), self.sub_label.cget("text"))

        self.ai_mgr.fetch_ai_quote(ctx, callback=_on_quote_received, dispatcher=lambda fn: self.root.after(0, fn))

    def get_dynamic_color_by_seconds(self, remaining_sec, is_elapsed=False):
        if not self.config.get("dynamic_time_color", True):
            return self.config.get("text_color", "#00FFCC")

        hrs = max(0.0, float(remaining_sec) / 3600.0)
        if hrs > 6.0:
            return "#EF4444"
        elif hrs > 3.0:
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
        if hasattr(self, "_task_dialog") and self._task_dialog:
            try:
                if self._task_dialog.winfo_exists():
                    self._task_dialog.lift()
                    self._task_dialog.focus_force()
                    return
            except Exception:
                pass
        self._task_dialog = QuickTaskDialog(self)
        self._bind_dialog_restore(self._task_dialog)

    def open_weather_dialog(self):
        if hasattr(self, "_weather_dialog") and self._weather_dialog:
            try:
                if self._weather_dialog.winfo_exists():
                    self._weather_dialog.lift()
                    self._weather_dialog.focus_force()
                    return
            except Exception:
                pass
        self._weather_dialog = WeatherForecastDialog(self)
        self._bind_dialog_restore(self._weather_dialog)

    def check_for_updates(self, interactive=False):
        """Kiểm tra bản cập nhật mới từ GitHub Releases (chỉ tự động chạy ngầm 1 lần/ngày khi khởi động)"""
        today_str = datetime.now().strftime("%Y-%m-%d")
        if not interactive:
            # Nếu là tự động kiểm tra ngầm, chỉ thực hiện nếu hôm nay chưa kiểm tra
            last_checked = self.config.get("last_update_check_date", "")
            if last_checked == today_str:
                return

        def _on_result(has_update, update_info, err):
            if not err:
                self.config["last_update_check_date"] = today_str
                self.save_config()

            if has_update and update_info:
                if hasattr(self, "_update_dialog") and self._update_dialog:
                    try:
                        if self._update_dialog.winfo_exists():
                            self._update_dialog.lift()
                            self._update_dialog.focus_force()
                            return
                    except Exception:
                        pass
                self._update_dialog = UpdateNotificationDialog(self, update_info)
                try:
                    self._update_dialog.bind(
                        "<Destroy>",
                        lambda e: self.root.after(50, self.ensure_window_visible) if e.widget is self._update_dialog else None,
                    )
                except Exception:
                    pass
                self.root.after(80, self.ensure_window_visible)
            elif interactive:
                if err:
                    self._safe_messagebox(
                        "showwarning",
                        "Kiểm tra cập nhật",
                        f"Không thể kết nối đến máy chủ GitHub:\n{err}",
                    )
                else:
                    self._safe_messagebox(
                        "showinfo",
                        "Kiểm tra cập nhật",
                        f"Bạn đang sử dụng phiên bản mới nhất ({APP_VERSION}) rồi nha! (づ｡◕‿‿◕｡)づ",
                    )

        self.update_mgr.check_for_updates(
            callback=_on_result,
            dispatcher=lambda fn: self.root.after(0, fn),
        )

    def toggle_autohide(self):
        new_val = not self.config.get("auto_hide", False)
        self.config["auto_hide"] = new_val

        # Loại trừ tương hỗ: Nếu bật Tự làm mờ thì bắt buộc tắt Xuyên chuột
        if new_val and self.config.get("click_through", False):
            self.config["click_through"] = False
            self.apply_click_through(False)

        self.save_config()
        # Hủy timer cũ + ép áp dụng sau khi menu đóng (reset flag kẹt)
        self._cancel_autohide_timer()
        self.root.after(200, lambda v=new_val: self._apply_autohide_after_toggle(v))

    def _apply_autohide_after_toggle(self, enabled):
        """Sau bật/tắt từ menu: clear flag kẹt rồi sync alpha đúng trạng thái."""
        self._heal_menu_open_flag(force_clear=True)
        if not enabled or not self.config.get("auto_hide", False):
            self._sync_autohide_alpha(force_full=True)
        else:
            self._sync_autohide_alpha(force_full=False)

    def _cancel_autohide_timer(self):
        pending = getattr(self, "_autohide_after", None)
        if pending:
            try:
                self.root.after_cancel(pending)
            except Exception:
                pass
        self._autohide_after = None

    def _heal_menu_open_flag(self, force_clear=False):
        """
        Sửa _is_menu_open bị kẹt True (Unmap menu đôi khi không chạy sau vài lần bật/tắt).
        Khi flag kẹt, auto-hide ngừng dim mãi.
        """
        if force_clear:
            self._is_menu_open = False
            self._current_menu = None
            return
        if not getattr(self, "_is_menu_open", False):
            return
        menu = getattr(self, "_current_menu", None)
        alive = False
        if menu is not None:
            try:
                alive = bool(menu.winfo_exists()) and bool(menu.winfo_ismapped())
            except Exception:
                alive = False
        if not alive:
            self._is_menu_open = False
            self._current_menu = None

    def _full_opacity(self):
        try:
            op = float(self.config.get("opacity", 0.90))
        except Exception:
            op = 0.90
        return max(0.15, min(1.0, op))

    def _dimmed_opacity(self):
        """Mờ rõ khi rời chuột, vẫn đủ nhìn (~40% sàn)."""
        full = self._full_opacity()
        return max(0.40, full * 0.40)

    def _set_window_alpha(self, alpha):
        try:
            a = max(0.15, min(1.0, float(alpha)))
            # Tránh gọi attributes lặp vô ích (giảm giật); vẫn ép khi lệch
            try:
                cur = float(self.root.attributes("-alpha"))
                if abs(cur - a) < 0.02:
                    return
            except Exception:
                pass
            self.root.attributes("-alpha", a)
        except Exception:
            pass

    def _pointer_over_clock(self):
        """Chuột còn nằm trong khung đồng hồ hay đã ra ngoài hẳn."""
        try:
            px, py = self.root.winfo_pointerxy()
            rx, ry = self.root.winfo_rootx(), self.root.winfo_rooty()
            rw, rh = self.root.winfo_width(), self.root.winfo_height()
            return rw > 1 and rh > 1 and rx <= px < rx + rw and ry <= py < ry + rh
        except Exception:
            return False

    def _sync_autohide_alpha(self, force_full=False):
        """Đặt alpha theo vị trí chuột. force_full dùng khi tắt tính năng."""
        self._autohide_after = None
        self._heal_menu_open_flag()
        if force_full or not self.config.get("auto_hide", False):
            self._set_window_alpha(self._full_opacity())
            return
        if getattr(self, "_is_menu_open", False):
            return
        try:
            if self._pointer_over_clock():
                self._set_window_alpha(self._full_opacity())
            else:
                self._set_window_alpha(self._dimmed_opacity())
        except Exception:
            pass

    def on_mouse_enter(self, event):
        if not self.config.get("auto_hide", False):
            return
        self._heal_menu_open_flag()
        if getattr(self, "_is_menu_open", False):
            return
        self._cancel_autohide_timer()
        self._set_window_alpha(self._full_opacity())

    def on_mouse_leave(self, event):
        # Enter/Leave KHÔNG bubble — bind từng widget.
        # Hoãn rồi đo pointer: chỉ dim khi chuột đã ra ngoài cả khung đồng hồ.
        if not self.config.get("auto_hide", False):
            return
        self._heal_menu_open_flag()
        if getattr(self, "_is_menu_open", False):
            return
        self._cancel_autohide_timer()
        self._autohide_after = self.root.after(60, self._sync_autohide_alpha)

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
            if hasattr(self, "pomo_ctrl_frame"):
                self.pomo_ctrl_frame.pack_forget()
            self.salary_daily_label.pack_forget()
            self.salary_month_label.pack_forget()
            self.task_label.pack_forget()
            self.sys_info_label.pack_forget()
            self.weather_label.pack_forget()
            self.sound_status_label.pack_forget()
            if hasattr(self, "mascot_label"):
                self.mascot_label.pack_forget()
            self.frame.configure(padx=10, pady=2)
        else:
            self.frame.configure(padx=16, pady=4)
            self.update_mascot_visibility()
            if self.config.get("show_sublabel", True):
                self.sub_label.pack(anchor="center", pady=(0, 1), before=self.main_row)
            if self.config.get("show_date", True) and self.current_mode == "clock":
                self.date_label.pack(anchor="center", pady=(1, 0))
            if self.config.get("show_quote", True):
                self.quote_label.pack(anchor="center", pady=(2, 0))
            self.update_pomo_ctrl_visibility()
            self.update_extra_info_visibility()

        self.adjust_size_and_position(initial=False)

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

        self.main_row = tk.Frame(self.frame, bg=self.config.get("bg_color", "#0f131a"))
        self.main_row.pack(anchor="center")

        self.mascot_label = tk.Label(
            self.main_row,
            bg=self.config.get("bg_color", "#0f131a"),
            cursor="hand2"
        )
        if self.config.get("show_mascot", True) and not self.config.get("mini_mode", False):
            self.mascot_label.pack(side="left", padx=(0, 6))

        self.time_label = tk.Label(
            self.main_row,
            text="00:00:00",
            font=("Consolas", self.config.get("font_size", 20), "bold"),
            bg=self.config.get("bg_color", "#0f131a"),
            fg=self.config.get("text_color", "#00FFCC")
        )
        self.time_label.pack(side="left")

        # Cập nhật sprite ban đầu cho bé mèo
        self.update_mascot_sprite(force=True)

        # Pomodoro Control Bar (chỉ hiển thị khi đang ở chế độ Pomodoro)
        self.pomo_ctrl_frame = tk.Frame(
            self.frame,
            bg=self.config.get("bg_color", "#0f131a")
        )
        btn_font = ("Segoe UI", 8, "bold")
        self.btn_pomo_toggle = tk.Button(
            self.pomo_ctrl_frame,
            text="▶ Bắt đầu",
            font=btn_font,
            bg="#059669",
            fg="#FFFFFF",
            activebackground="#10B981",
            activeforeground="#FFFFFF",
            bd=0,
            padx=7,
            pady=2,
            relief="flat",
            cursor="hand2",
            command=self.toggle_pomodoro
        )
        self.btn_pomo_toggle.pack(side="left", padx=2)

        self.btn_pomo_reset = tk.Button(
            self.pomo_ctrl_frame,
            text="🔄 Đặt lại",
            font=btn_font,
            bg="#1E293B",
            fg="#94A3B8",
            activebackground="#334155",
            activeforeground="#F8FAFC",
            bd=0,
            padx=6,
            pady=2,
            relief="flat",
            cursor="hand2",
            command=self.reset_pomodoro
        )
        self.btn_pomo_reset.pack(side="left", padx=2)

        self.btn_pomo_skip = tk.Button(
            self.pomo_ctrl_frame,
            text="⏭ Bỏ qua",
            font=btn_font,
            bg="#1E293B",
            fg="#94A3B8",
            activebackground="#334155",
            activeforeground="#F8FAFC",
            bd=0,
            padx=6,
            pady=2,
            relief="flat",
            cursor="hand2",
            command=self.skip_pomodoro_stage
        )
        self.btn_pomo_skip.pack(side="left", padx=2)

        if self.current_mode == "pomodoro" and not self.config.get("mini_mode", False):
            self.pomo_ctrl_frame.pack(anchor="center", pady=(2, 2))

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
            if self.quote_label.winfo_manager():
                self.date_label.pack(anchor="center", pady=(1, 0), before=self.quote_label)
            elif self.salary_daily_label.winfo_manager():
                self.date_label.pack(anchor="center", pady=(1, 0), before=self.salary_daily_label)
            elif self.task_label.winfo_manager():
                self.date_label.pack(anchor="center", pady=(1, 0), before=self.task_label)
            elif self.sys_info_label.winfo_manager():
                self.date_label.pack(anchor="center", pady=(1, 0), before=self.sys_info_label)
            elif self.weather_label.winfo_manager():
                self.date_label.pack(anchor="center", pady=(1, 0), before=self.weather_label)
            elif self.sound_status_label.winfo_manager():
                self.date_label.pack(anchor="center", pady=(1, 0), before=self.sound_status_label)
            elif hasattr(self, "pomo_ctrl_frame") and self.pomo_ctrl_frame.winfo_manager():
                self.date_label.pack(anchor="center", pady=(1, 0), after=self.pomo_ctrl_frame)
            else:
                self.date_label.pack(anchor="center", pady=(1, 0), after=self.main_row)
        else:
            self.date_label.pack_forget()

    def update_quote_visibility(self):
        if self.config.get("mini_mode", False):
            self.quote_label.pack_forget()
            return
        if self.config.get("show_quote", True):
            if self.salary_daily_label.winfo_manager():
                self.quote_label.pack(anchor="center", pady=(2, 0), before=self.salary_daily_label)
            elif self.task_label.winfo_manager():
                self.quote_label.pack(anchor="center", pady=(2, 0), before=self.task_label)
            elif self.sys_info_label.winfo_manager():
                self.quote_label.pack(anchor="center", pady=(2, 0), before=self.sys_info_label)
            elif self.weather_label.winfo_manager():
                self.quote_label.pack(anchor="center", pady=(2, 0), before=self.weather_label)
            elif self.sound_status_label.winfo_manager():
                self.quote_label.pack(anchor="center", pady=(2, 0), before=self.sound_status_label)
            elif self.date_label.winfo_manager():
                self.quote_label.pack(anchor="center", pady=(2, 0), after=self.date_label)
            elif hasattr(self, "pomo_ctrl_frame") and self.pomo_ctrl_frame.winfo_manager():
                self.quote_label.pack(anchor="center", pady=(2, 0), after=self.pomo_ctrl_frame)
            else:
                self.quote_label.pack(anchor="center", pady=(2, 0), after=self.main_row)
        else:
            self.quote_label.pack_forget()

    def update_sublabel_visibility(self):
        if self.config.get("mini_mode", False):
            self.sub_label.pack_forget()
            return
        if self.config.get("show_sublabel", True):
            self.sub_label.pack(anchor="center", pady=(0, 1), before=self.main_row)
        else:
            self.sub_label.pack_forget()

    def update_pomo_ctrl_visibility(self):
        if not hasattr(self, "pomo_ctrl_frame"):
            return
        if self.config.get("mini_mode", False) or self.current_mode != "pomodoro":
            self.pomo_ctrl_frame.pack_forget()
        else:
            if self.date_label.winfo_manager():
                self.pomo_ctrl_frame.pack(anchor="center", pady=(2, 2), before=self.date_label)
            elif self.quote_label.winfo_manager():
                self.pomo_ctrl_frame.pack(anchor="center", pady=(2, 2), before=self.quote_label)
            else:
                self.pomo_ctrl_frame.pack(anchor="center", pady=(2, 2), after=self.main_row)
            self._update_pomo_ctrl_ui()

    def toggle_focus_sound(self):
        st = self.config.get("focus_sound", {}).get("sound_type", "rain")
        self.focus_sound_mgr.toggle(
            sound_type=st,
            callback=lambda ok, msg: self.root.after(0, self.update_extra_info_visibility)
        )
        self.update_extra_info_visibility()

    def select_and_play_sound(self, sound_type):
        self.config.setdefault("focus_sound", {})["sound_type"] = sound_type
        self.config["focus_sound"]["enabled"] = True
        self.save_config()
        self.focus_sound_mgr.play(
            sound_type=sound_type,
            callback=lambda ok, msg: self.root.after(0, self.update_extra_info_visibility)
        )
        self.update_extra_info_visibility()

    def refresh_weather(self):
        self.weather_mgr.fetch_weather(
            callback=lambda txt, data: self.update_extra_info_visibility(),
            dispatcher=lambda fn: self.root.after(0, fn)
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
            title_txt = self.focus_sound_mgr.current_title or snd_info.get("name", "Âm thanh tập trung")
            # Cắt ngắn nếu tiêu đề quá dài
            if len(title_txt) > 28:
                title_txt = title_txt[:25] + "..."
            self.sound_status_label.configure(text=f"Playing: {icon} {title_txt}")
            self.sound_status_label.pack(anchor="center", pady=(1, 0))
        else:
            self.sound_status_label.pack_forget()

        self.adjust_size_and_position(initial=False)

    def setup_bindings(self):
        # Chỉ bind lên các widget giao diện bên trong, KHÔNG bind self.root để tránh Tkinter bubble nhân đôi sự kiện chuột
        widgets = [self.frame, self.main_row, self.time_label, self.sub_label, self.date_label,
                   self.salary_daily_label, self.salary_month_label, self.task_label,
                   self.sys_info_label, self.weather_label, self.sound_status_label]
        if hasattr(self, "pomo_ctrl_frame"):
            widgets.append(self.pomo_ctrl_frame)

        for w in widgets:
            w.bind("<ButtonPress-1>", self.start_drag)
            w.bind("<B1-Motion>", self.do_drag)
            w.bind("<ButtonRelease-1>", self.stop_drag)
            w.bind("<Button-3>", self.show_context_menu)
            w.bind("<Double-Button-1>", self.on_double_click)

        # Quote label: cho phép kéo thả, nhả chuột đổi quote, chặn double-click đè lên mini mode
        self.quote_label.bind("<ButtonPress-1>", self.start_drag)
        self.quote_label.bind("<B1-Motion>", self.do_drag)
        self.quote_label.bind("<ButtonRelease-1>", self._on_quote_release)
        self.quote_label.bind("<Double-Button-1>", lambda e: "break")
        self.quote_label.bind("<Button-3>", self.show_context_menu)

        # Mascot interactions: kéo thả, click kêu meow, chặn double-click đè lên mini mode
        self.mascot_label.bind("<ButtonPress-1>", self.start_drag)
        self.mascot_label.bind("<B1-Motion>", self.do_drag)
        self.mascot_label.bind("<ButtonRelease-1>", self._on_mascot_release)
        self.mascot_label.bind("<Double-Button-1>", lambda e: "break")
        self.mascot_label.bind("<Button-3>", self.show_context_menu)

        # Auto-hide: Enter/Leave không bubble lên root — bind mọi widget nhìn thấy
        hover_widgets = [
            self.root, self.frame, self.main_row, self.time_label, self.sub_label,
            self.date_label, self.quote_label, self.mascot_label,
            self.salary_daily_label, self.salary_month_label, self.task_label,
            self.sys_info_label, self.weather_label, self.sound_status_label,
        ]
        if hasattr(self, "pomo_ctrl_frame"):
            hover_widgets.append(self.pomo_ctrl_frame)
        for w in hover_widgets:
            w.bind("<Enter>", self.on_mouse_enter, add="+")
            w.bind("<Leave>", self.on_mouse_leave, add="+")

        # Keyboard shortcuts (F8 được quản lý độc quyền bởi Win32 GlobalHotkeyManager)
        self.root.bind("<p>", lambda e: self.toggle_mascot())
        self.root.bind("<P>", lambda e: self.toggle_mascot())
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
        self.root.bind("<w>", lambda e: self.open_weather_dialog())
        self.root.bind("<W>", lambda e: self.open_weather_dialog())
        self.root.bind("<h>", lambda e: self.toggle_autohide())
        self.root.bind("<H>", lambda e: self.toggle_autohide())
        self.root.bind("<space>", lambda e: self.on_space_key())

    def toggle_mascot(self):
        self.config["show_mascot"] = not self.config.get("show_mascot", True)
        self.update_mascot_visibility()
        self.save_config()

    def update_mascot_visibility(self):
        if not hasattr(self, "mascot_label"):
            return
        if self.config.get("show_mascot", True) and not self.config.get("mini_mode", False):
            self.mascot_label.pack(side="left", padx=(0, 6), before=self.time_label)
            self.update_mascot_sprite(force=True)
        else:
            self.mascot_label.pack_forget()
        self.adjust_size_and_position(initial=False)

    def _close_mascot_bubble(self):
        if hasattr(self, "_bubble_timer") and self._bubble_timer:
            try:
                self.root.after_cancel(self._bubble_timer)
            except Exception:
                pass
            self._bubble_timer = None

        if hasattr(self, "_mascot_bubble") and self._mascot_bubble:
            try:
                if self._mascot_bubble.winfo_exists():
                    self._mascot_bubble.destroy()
            except Exception:
                pass
            self._mascot_bubble = None

    def show_mascot_speech_bubble(self, text):
        self._close_mascot_bubble()
        try:
            bubble = tk.Toplevel(self.root)
            bubble.withdraw()
            bubble.overrideredirect(True)
            bubble.attributes("-topmost", True)
            bubble.attributes("-alpha", 0.95)
            bubble.configure(bg="#0f172a")

            frame = tk.Frame(
                bubble,
                bg="#1e2430",
                padx=8,
                pady=4,
                highlightbackground="#38BDF8",
                highlightthickness=1
            )
            frame.pack(fill="both", expand=True)

            lbl = tk.Label(
                frame,
                text=text,
                font=("Segoe UI", 8, "bold"),
                bg="#1e2430",
                fg="#F8FAFC"
            )
            lbl.pack()

            bubble.update_idletasks()
            bw = bubble.winfo_reqwidth()
            bh = bubble.winfo_reqheight()

            # Vị trí: nổi ngay phía trên đầu bé mèo
            mx = self.mascot_label.winfo_rootx()
            my = self.mascot_label.winfo_rooty()

            bx = max(10, mx - (bw // 3))
            by = my - bh - 6
            if by < 10:  # Nếu sát mép trên màn hình thì hiện phía dưới
                by = my + self.mascot_label.winfo_height() + 6

            bubble.geometry(f"{bw}x{bh}+{bx}+{by}")
            bubble.deiconify()
            self._mascot_bubble = bubble
            bubble.after(0, lambda: hide_from_taskbar(bubble))

            # Tự động đóng bong bóng thoại sau 3.0 giây (hủy bỏ timer cũ nếu người dùng click liên tiếp)
            self._bubble_timer = self.root.after(3000, self._close_mascot_bubble)
        except Exception:
            pass

    def on_mascot_click(self, event=None):
        now_ts = time.time()
        # Chống click dồn dập (debounce 350ms)
        if now_ts - getattr(self, "_last_mascot_click_ts", 0) < 0.35:
            return "break"
        self._last_mascot_click_ts = now_ts

        sound_mgr.play_tick()
        # Kích hoạt trạng thái vui sướng nhảy nhót trong 3.0 giây (đúng 2 chu kỳ nhảy hoàn chỉnh)
        self._mascot_happy_until = time.time() + 3.0
        meow = self.mascot_mgr.get_random_meow()
        self.show_mascot_speech_bubble(meow)
        return "break"

    def is_near_departure_time(self, now):
        try:
            today_dep, _ = self.get_today_departure_info(now)
            today_str = now.strftime("%Y-%m-%d")
            dt_dep = datetime.strptime(f"{today_str} {today_dep}", "%Y-%m-%d %H:%M:%S")
            diff_min = (dt_dep - now).total_seconds() / 60.0
            # Chỉ coi là sắp tan làm trong vòng 30 phút trước giờ tan làm
            return 0 <= diff_min <= 30
        except Exception:
            return False

    def set_mascot_action(self, action):
        self.config["mascot_action"] = action
        self.save_config()
        self.update_mascot_sprite(force=True)

    def update_mascot_sprite(self, force=False):
        if not self.config.get("show_mascot", True) or self.config.get("mini_mode", False):
            return

        # Nếu vừa được click cưng nựng, mèo chuyển sang nhảy nhót vui sướng trong 3 giây
        if getattr(self, "_mascot_happy_until", 0) > time.time():
            state = "leaving"
        else:
            configured_action = self.config.get("mascot_action", "auto")
            if configured_action in ("idle", "work", "leaving", "sleep"):
                state = configured_action
            else:
                now = datetime.now()
                is_leaving_soon = self.is_near_departure_time(now)
                state = self.mascot_mgr.get_state(
                    current_mode=self.current_mode,
                    pomo_running=self.pomo_running,
                    pomo_stage=self.pomo_stage,
                    is_leaving_soon=is_leaving_soon,
                    now=now
                )

        now_ts = time.time()
        img = self.mascot_mgr.get_animated_sprite(state, now_ts)
        if img and (force or getattr(self.mascot_label, "image", None) != img):
            self.mascot_label.configure(image=img)
            self.mascot_label.image = img

    def _on_mascot_release(self, event):
        self.stop_drag(event)
        if not getattr(self, "drag_moved", False):
            self.on_mascot_click(event)
        return "break"

    def _on_quote_release(self, event):
        self.stop_drag(event)
        if not getattr(self, "drag_moved", False):
            self.request_next_quote()
        return "break"

    def start_drag(self, event):
        if not self.config["locked"]:
            self.drag_start_x = event.x_root - self.root.winfo_x()
            self.drag_start_y = event.y_root - self.root.winfo_y()
            self.drag_moved = False
        return "break"

    def do_drag(self, event):
        if not self.config["locked"]:
            self.drag_moved = True
            x = event.x_root - self.drag_start_x
            y = event.y_root - self.drag_start_y
            # Multi-monitor drag fix: Cho phép di chuyển mượt mà trên nhiều màn hình
            self.root.geometry(f"+{x}+{y}")
        return "break"

    def stop_drag(self, event=None):
        # Chỉ lưu cấu hình khi vị trí thực sự bị di dời (tránh ghi đĩa vô ích mỗi lần click chuột)
        if getattr(self, "drag_moved", False):
            self.save_config()
            self.drag_moved = False
        return "break"

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
            self.toggle_pomodoro()
        else:
            self.toggle_mini_mode()
        return "break"

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
        elif self.current_mode == "pomodoro":
            self.toggle_pomodoro()

    def _close_context_menu(self):
        old = getattr(self, "_current_menu", None)
        self._is_menu_open = False
        self._current_menu = None
        try:
            if old:
                old.unpost()
        except Exception:
            pass

    def show_context_menu(self, event):
        """Menu chuột phải — giữ logic đơn giản, không đụng topmost/alpha của đồng hồ."""
        self._close_context_menu()
        self._is_menu_open = True
        self._menu_generation = getattr(self, "_menu_generation", 0) + 1
        gen = self._menu_generation

        menu = ContextMenuBuilder.build(self, parent=self.root)
        self._current_menu = menu

        def _on_menu_dismiss():
            # Chỉ nhận Unmap của đúng generation hiện tại (tránh race bật/tắt nhiều lần)
            if getattr(self, "_menu_generation", 0) != gen:
                return
            if self._current_menu is not None and self._current_menu is not menu:
                return
            self._is_menu_open = False
            if self._current_menu is menu:
                self._current_menu = None
            self.root.after(80, self._sync_autohide_alpha)

        menu.bind("<Unmap>", lambda e: self.root.after(50, _on_menu_dismiss))

        # Kẹp trong màn hình để khỏi tràn đáy (ước lượng đơn giản)
        try:
            end_idx = menu.index("end")
            n = 0 if end_idx is None else int(end_idx) + 1
        except Exception:
            n = 18
        mh, mw = max(120, n * 28 + 20), 340
        x, y = int(event.x_root), int(event.y_root)
        try:
            vx, vy, vw, vh = get_virtual_screen_rect()
            if y + mh > vy + vh - 8:
                y = max(vy + 8, y - mh)
            if x + mw > vx + vw - 8:
                x = max(vx + 8, vx + vw - mw - 8)
        except Exception:
            pass

        try:
            menu.tk_popup(x, y)
        finally:
            try:
                menu.grab_release()
            except Exception:
                pass
        return "break"

    def open_control_center(self, initial_tab=0):
        if hasattr(self, "_ctrl_dialog") and self._ctrl_dialog:
            try:
                if self._ctrl_dialog.winfo_exists():
                    self._ctrl_dialog.lift()
                    self._ctrl_dialog.focus_force()
                    if initial_tab is not None:
                        try:
                            self._ctrl_dialog.notebook.select(initial_tab)
                        except Exception:
                            pass
                    return
            except Exception:
                pass
        self._ctrl_dialog = ControlCenterDialog(self, initial_tab=initial_tab)
        self._bind_dialog_restore(self._ctrl_dialog)

    def activate_today_departure(self):
        now = datetime.now()
        today_dep, today_tag = self.get_today_departure_info(now)
        self.config["target_time_str"] = today_dep
        self.config["target_time_label"] = f"Tan làm ({today_tag})"
        self.config["target_time_active"] = True
        self.config["target_time_is_work"] = True
        self.switch_mode("target_time")
        self.save_config()

    def switch_mode(self, mode_name):
        self.current_mode = mode_name
        self.config["mode"] = mode_name
        self.update_date_visibility()
        self.update_sublabel_visibility()
        self.update_pomo_ctrl_visibility()
        self.adjust_size_and_position(initial=False)
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
        # Restart / Start khi remaining đã về 0 phải nạp lại duration — tránh loop báo thức
        if self.timer_remaining <= 0:
            self.timer_remaining = max(1, int(self.timer_duration) or 300)
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
            ALERT_MESSAGES["timer_finished_title"],
            ALERT_MESSAGES["timer_finished_body"],
            on_dismiss=self._dialog_closed_then(),
            on_restart=self._dialog_closed_then(self.start_timer)
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
    def toggle_pomodoro(self):
        self.pomo_running = not self.pomo_running
        self.pomo_last_tick = time.time()
        self._update_pomo_ctrl_ui()

    def reset_pomodoro(self):
        self.pomo_running = False
        if self.pomo_stage == "work":
            self.pomo_remaining = self.config.get("pomo_work_min", 25) * 60
        elif self.pomo_stage == "break":
            self.pomo_remaining = self.config.get("pomo_break_min", 5) * 60
        else:
            self.pomo_remaining = self.config.get("pomo_long_break_min", 15) * 60
        self.pomo_last_tick = time.time()
        self._update_pomo_ctrl_ui()

    def _pomo_cycles(self):
        try:
            return max(1, int(self.config.get("pomo_cycles", 4) or 4))
        except Exception:
            return 4

    def skip_pomodoro_stage(self):
        self.pomo_running = False
        if self.pomo_stage == "work":
            self.pomo_cycle_count += 1
            if self.pomo_cycle_count % self._pomo_cycles() == 0:
                self.start_pomodoro_break(is_long=True)
            else:
                self.start_pomodoro_break(is_long=False)
        else:
            self.start_pomodoro_work()
        self._update_pomo_ctrl_ui()

    def _update_pomo_ctrl_ui(self):
        if not hasattr(self, "btn_pomo_toggle"):
            return
        self._last_pomo_btn_running = self.pomo_running
        if self.pomo_running:
            self.btn_pomo_toggle.configure(text="⏸ Tạm dừng", bg="#DC2626", activebackground="#EF4444")
        else:
            self.btn_pomo_toggle.configure(text="▶ Bắt đầu", bg="#059669", activebackground="#10B981")

    def start_pomodoro_work(self):
        self.pomo_stage = "work"
        self.pomo_remaining = self.config.get("pomo_work_min", 25) * 60
        self.pomo_running = True
        self._update_pomo_ctrl_ui()

    def start_pomodoro_break(self, is_long=False):
        if is_long:
            self.pomo_stage = "long_break"
            self.pomo_remaining = self.config.get("pomo_long_break_min", 15) * 60
        else:
            self.pomo_stage = "break"
            self.pomo_remaining = self.config.get("pomo_break_min", 5) * 60
        self.pomo_running = True
        self._update_pomo_ctrl_ui()

    def trigger_pomodoro_stage_complete(self):
        self.pomo_running = False
        if self.pomo_stage == "work":
            self.pomo_cycle_count += 1
            sound_mgr.play_pomo_break()
            if self.pomo_cycle_count % self._pomo_cycles() == 0:
                msg = ALERT_MESSAGES["pomo_long_break_body"].format(cycle=self.pomo_cycle_count)
                is_long = True
            else:
                msg = ALERT_MESSAGES["pomo_short_break_body"]
                is_long = False

            AlertNotificationDialog(
                self.root,
                ALERT_MESSAGES["pomo_work_complete_title"],
                msg,
                on_dismiss=self._dialog_closed_then(lambda: self.start_pomodoro_break(is_long))
            )
        else:
            sound_mgr.play_pomo_break()
            msg = ALERT_MESSAGES["pomo_break_complete_body"]
            AlertNotificationDialog(
                self.root,
                ALERT_MESSAGES["pomo_break_complete_title"],
                msg,
                on_dismiss=self._dialog_closed_then(lambda: self.start_pomodoro_work())
            )

    # ---------------- ⏰ ALARMS CHECKER ----------------
    def check_alarms(self, now):
        cur_hm = now.strftime("%H:%M")
        # Dedup theo (ngày + HH:MM) để không miss sau sleep và không bắn lại trong cùng phút
        check_key = f"{now.strftime('%Y-%m-%d')} {cur_hm}"
        if check_key == getattr(self, "_last_alarm_check_key", ""):
            return
        self._last_alarm_check_key = check_key
        self.last_alarm_checked_min = now.minute

        alarms = self.config.get("alarms", [])
        changed = False
        for alm in list(alarms):
            if alm.get("enabled", False) and alm.get("time") == cur_hm:
                self.trigger_alarm_alert(alm)
                if not alm.get("repeat", True):
                    # One-shot / snooze: gỡ hẳn khỏi list sau khi kêu (tránh phình JSON)
                    if alm.get("is_snooze") or alm.get("id") == "__snooze__":
                        try:
                            alarms.remove(alm)
                        except ValueError:
                            alm["enabled"] = False
                    else:
                        alm["enabled"] = False
                    changed = True
        if changed:
            self.save_config()

    def trigger_alarm_alert(self, alm):
        sound_mgr.play_alarm_loop(alm.get("label", "Báo thức"))

        label_txt = alm.get("label", "Báo thức")
        time_txt = alm.get("time", "")

        def snooze_action():
            snooze_dt = datetime.now() + timedelta(minutes=5)
            snooze_time = snooze_dt.strftime("%H:%M")
            snooze_lbl = ALERT_MESSAGES["alarm_snooze_label"].format(label=label_txt)
            alarms = self.config.setdefault("alarms", [])
            # Chỉ giữ 1 entry snooze — ghi đè thay vì append mãi
            existing = next((a for a in alarms if a.get("is_snooze") or a.get("id") == "__snooze__"), None)
            payload = {
                "id": "__snooze__",
                "time": snooze_time,
                "label": snooze_lbl,
                "enabled": True,
                "repeat": False,
                "is_snooze": True,
            }
            if existing:
                existing.update(payload)
            else:
                alarms.append(payload)
            self.save_config()

        AlertNotificationDialog(
            self.root,
            ALERT_MESSAGES["alarm_title"].format(time_str=time_txt),
            ALERT_MESSAGES["alarm_body"].format(time_str=time_txt, label=label_txt),
            on_dismiss=self._dialog_closed_then(),
            on_snooze=self._dialog_closed_then(snooze_action)
        )

    # ---------------- 💧 WATER REMINDER CHECKER ----------------
    def check_water_reminder(self):
        w_cfg = self.config.get("water_reminder", {"enabled": True, "interval_min": 45})
        if not w_cfg.get("enabled", True):
            return

        # Tránh mở chồng chéo nhiều dialog nếu người dùng chưa bấm tắt dialog cũ
        if hasattr(self, "_hydration_dialog") and self._hydration_dialog:
            try:
                if self._hydration_dialog.winfo_exists():
                    return
            except Exception:
                pass

        interval_sec = w_cfg.get("interval_min", 45) * 60
        if time.time() - self.last_water_remind_time >= interval_sec:
            self.last_water_remind_time = time.time()
            sound_mgr.play_water_chime()
            try:
                self._hydration_dialog = HydrationReminderDialog(self.root)
                self._hydration_dialog.bind(
                    "<Destroy>",
                    lambda e: self.root.after(50, self.ensure_window_visible) if e.widget is self._hydration_dialog else None,
                )
            except Exception:
                pass

    # ---------------- 🎯 TARGET TIME CHECKER ----------------
    def check_target_time(self, now):
        if not self.config.get("target_time_active", False):
            return
        # Chỉ tin cờ target_time_is_work — không heuristic theo nhãn "Tan làm"
        # (tránh ghi đè mốc tùy chỉnh có nhãn bắt đầu bằng "Tan làm")
        is_work = bool(self.config.get("target_time_is_work", True))
        today_str = now.strftime("%Y-%m-%d")
        if is_work:
            # Chủ nhật không có ca làm → không báo tan làm
            if now.weekday() == 6:
                return
            today_dep, today_tag = self.get_today_departure_info(now)
            tgt_str = today_dep
            lbl = f"Tan làm ({today_tag})"
            if getattr(self, "_last_work_departure_alert_date", None) == today_str:
                return
        else:
            tgt_str = self.config.get("target_time_str", "17:45:00")
            lbl = self.config.get("target_time_label", "Tan làm")

        try:
            norm_tgt = self._normalize_time_str(tgt_str, "17:45:00")
            tgt_dt = datetime.strptime(f"{today_str} {norm_tgt}", "%Y-%m-%d %H:%M:%S")
            diff = (tgt_dt - now).total_seconds()
            # Cho phép bắt kịp tối đa 10 phút sau mốc (sleep/lag) — cửa sổ ±2s trước đây dễ miss
            if -600 <= diff <= 1:
                if is_work:
                    self._last_work_departure_alert_date = today_str
                else:
                    self.config["target_time_active"] = False
                    self.save_config()
                sound_mgr.play_alarm_loop("Đã đến giờ mục tiêu!")
                AlertNotificationDialog(
                    self.root,
                    ALERT_MESSAGES["target_reached_title"].format(time_str=tgt_str[:5]),
                    ALERT_MESSAGES["target_reached_body"].format(time_str=tgt_str[:5], label=lbl),
                    on_dismiss=self._dialog_closed_then()
                )
        except Exception:
            pass

    def _dialog_closed_then(self, *callbacks):
        """Chạy callback rồi kéo đồng hồ hiện lại (tránh mất cửa sổ sau Toplevel/messagebox)."""
        def _runner(*_args):
            for cb in callbacks:
                if not cb:
                    continue
                try:
                    cb()
                except Exception:
                    pass
            try:
                self.root.after(50, self.ensure_window_visible)
            except Exception:
                pass
        return _runner

    def _bind_dialog_restore(self, dialog):
        """Khi đóng Toplevel con, khôi phục đồng hồ nổi (bug Tk overrideredirect trên Windows)."""
        if not dialog:
            return
        try:
            dialog.bind(
                "<Destroy>",
                lambda e, d=dialog: self.root.after(50, self.ensure_window_visible) if e.widget is d else None,
            )
        except Exception:
            pass

    def _safe_messagebox(self, kind, title, message):
        """
        messagebox với parent overrideredirect trên Windows dễ withdraw cửa sổ chính
        sau khi đóng hộp thoại — luôn khôi phục hiển thị sau đó.
        """
        fn = getattr(messagebox, kind, None)
        if not fn:
            return None
        try:
            return fn(title, message, parent=self.root)
        finally:
            self.root.after(50, self.ensure_window_visible)

    def _clamp_on_screen(self, margin=24):
        """Nếu đồng hồ nằm hoàn toàn ngoài desktop ảo (tháo monitor / đổi DPI) thì kéo lại vào."""
        try:
            self.root.update_idletasks()
            x = self.root.winfo_x()
            y = self.root.winfo_y()
            w = max(self.root.winfo_width(), self.frame.winfo_reqwidth() + 12, 40)
            h = max(self.root.winfo_height(), self.frame.winfo_reqheight() + 4, 20)
            vx, vy, vw, vh = get_virtual_screen_rect()
            if vw <= 0 or vh <= 0:
                return False

            fully_off = (x + w < vx + margin) or (x > vx + vw - margin) or (y + h < vy + margin) or (y > vy + vh - margin)
            if not fully_off:
                return False

            new_x = min(max(x, vx + margin), vx + vw - w - margin)
            new_y = min(max(y, vy + margin), vy + vh - h - margin)
            # Fallback nếu size lớn hơn cả desktop
            if new_x < vx:
                new_x = vx + margin
            if new_y < vy:
                new_y = vy + margin
            self.root.geometry(f"{w}x{h}+{int(new_x)}+{int(new_y)}")
            self.config["x"] = int(new_x)
            self.config["y"] = int(new_y)
            return True
        except Exception:
            return False

    def ensure_window_visible(self, restore_alpha=False):
        """
        Chống đồng hồ 'tự biến mất': withdraw sau dialog, mất topmost sau sleep/fullscreen,
        alpha về 0, hoặc tọa độ lệch khỏi mọi màn hình. Không có nút taskbar nên phải tự kéo lại.
        """
        if getattr(self, "_is_closing", False):
            return
        # Đang mở context menu: không ép topmost kẻo đè menu xuống dưới đồng hồ
        if getattr(self, "_is_menu_open", False):
            return
        try:
            if not self.root.winfo_exists():
                return

            need_remap = False
            try:
                if self.root.state() == "withdrawn":
                    need_remap = True
            except Exception:
                pass
            try:
                if not self.root.winfo_viewable():
                    need_remap = True
            except Exception:
                pass
            if not is_window_visible_win32(self.root):
                need_remap = True

            if need_remap:
                self.root.deiconify()
                hide_from_taskbar(self.root)
                # Không gọi lại set_click_through ở đây — SetWindowPos lặp làm đơ mascot

            # Kích thước đổ sập về 1px (hiếm, sau lỗi layout) → đo lại
            try:
                if self.root.winfo_width() < 20 or self.root.winfo_height() < 10:
                    self.adjust_size_and_position(initial=False)
            except Exception:
                pass

            clamped = self._clamp_on_screen()
            if clamped:
                try:
                    self.save_config()
                except Exception:
                    pass

            # Topmost nhẹ: chỉ Tk attributes thường xuyên; Win32 khi vừa remap
            try:
                self.root.attributes("-topmost", True)
            except Exception:
                pass
            if need_remap:
                force_topmost(self.root)

            if restore_alpha:
                self._sync_autohide_alpha()
            else:
                try:
                    alpha = float(self.root.attributes("-alpha"))
                    if alpha <= 0.05:
                        self._sync_autohide_alpha()
                except Exception:
                    pass
        except Exception:
            pass

    # ---------------- 🔄 MASTER UPDATE LOOP ----------------
    def update_loop(self):
        if getattr(self, "_is_closing", False):
            return
        try:
            if not self.root.winfo_exists():
                return
            now = datetime.now()
            cur_sec = int(now.timestamp())

            # Mỗi ~4s kiểm tra cửa sổ còn hiện không (sau sleep, dialog, đổi monitor...)
            if cur_sec - int(getattr(self, "_last_visibility_check", 0)) >= 4:
                self._last_visibility_check = cur_sec
                self.ensure_window_visible()

            self.check_alarms(now)
            self.check_target_time(now)
            self.check_water_reminder()
            # Timer / Pomodoro phải đếm dù đang xem mode khác (trước đây chỉ tick khi render mode đó)
            self._tick_timer_and_pomodoro()

            # Auto-hide: poll pointer — nguồn chính, tự heal flag menu kẹt
            if self.config.get("auto_hide", False):
                now_ts = time.time()
                if now_ts - getattr(self, "_last_autohide_poll_ts", 0) >= 0.30:
                    self._last_autohide_poll_ts = now_ts
                    self._heal_menu_open_flag()
                    if not getattr(self, "_is_menu_open", False):
                        self._sync_autohide_alpha()

            # Rotate quote: offline ~45s; có AI key thì theo auto_refresh_min
            ai_cfg = self.config.get("ai_quotes", {})
            if ai_cfg.get("enabled", True) and str(ai_cfg.get("api_key", "")).strip():
                try:
                    quote_interval = max(60, int(ai_cfg.get("auto_refresh_min", 15) or 15) * 60)
                except Exception:
                    quote_interval = 900
            else:
                quote_interval = 45
            if time.time() - self.last_quote_update_time > quote_interval:
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

            # Cập nhật trạng thái thú cưng Pixel Cat
            self.update_mascot_sprite()

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
            if not getattr(self, "_is_closing", False):
                try:
                    self.root.after(50, self.update_loop)
                except Exception:
                    pass

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
                norm_dep = self._normalize_time_str(today_dep, "17:45:00")
                dt_dep = datetime.strptime(f"{today_str} {norm_dep}", "%Y-%m-%d %H:%M:%S")
                rem_sec = (dt_dep - now).total_seconds()
                fg_col = self.get_dynamic_color_by_seconds(rem_sec)
            except Exception:
                fg_col = self.config.get("text_color", "#00FFCC")
        else:
            fg_col = self.config.get("text_color", "#00FFCC")

        self.time_label.configure(text=time_str, fg=fg_col)

        next_alm = self._get_next_upcoming_alarm(now)
        if next_alm:
            sub_txt = f"{mascot_prefix}🕒 CLOCK  •  ⏰ {next_alm.get('time', '')}"
        else:
            sub_txt = f"{mascot_prefix}🕒 CLOCK"

        self.sub_label.configure(text=sub_txt, fg="#94A3B8")

        if self.config.get("show_date", True) and not self.config.get("mini_mode", False):
            vn_days = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ Nhật"]
            date_str = f"{vn_days[now.weekday()]}, {now.strftime('%d/%m/%Y')}"
            self.date_label.configure(text=date_str)

        self._check_and_resize(time_str, sub_txt)

    def _tick_timer_and_pomodoro(self):
        """Cập nhật đếm ngược timer/pomodoro ngay cả khi đang xem clock / target time."""
        now_ts = time.time()
        if self.timer_state == "running":
            delta = now_ts - self.timer_last_tick
            self.timer_last_tick = now_ts
            self.timer_remaining -= delta
            if self.timer_remaining <= 0:
                self.timer_remaining = 0
                self.trigger_timer_finished()

        if self.pomo_running:
            delta = now_ts - self.pomo_last_tick
            self.pomo_last_tick = now_ts
            self.pomo_remaining -= delta
            if self.pomo_remaining <= 0:
                self.pomo_remaining = 0
                self.trigger_pomodoro_stage_complete()

    def _render_timer_mode(self, mascot_prefix):
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

    def _get_next_upcoming_alarm(self, now):
        """Báo thức sắp tới theo giờ thực (không sort lexicographic sai lúc tối)."""
        active = [a for a in self.config.get("alarms", []) if a.get("enabled", False) and a.get("time")]
        if not active:
            return None
        cur = now.strftime("%H:%M")
        upcoming = sorted(
            [a for a in active if str(a.get("time", "")) >= cur],
            key=lambda x: str(x.get("time", "")),
        )
        if upcoming:
            return upcoming[0]
        return sorted(active, key=lambda x: str(x.get("time", "")))[0]

    def _render_target_time_mode(self, now, mascot_prefix):
        is_work = bool(self.config.get("target_time_is_work", True))
        if is_work:
            today_dep, today_tag = self.get_today_departure_info(now)
            tgt_str = today_dep
            lbl = f"Tan làm ({today_tag})"
            if self.config.get("target_time_str") != tgt_str or self.config.get("target_time_label") != lbl:
                self.config["target_time_str"] = tgt_str
                self.config["target_time_label"] = lbl
                self.save_config()
        else:
            tgt_str = self.config.get("target_time_str", "17:45:00")
            lbl = self.config.get("target_time_label", "Tan làm")

        try:
            today_str = now.strftime("%Y-%m-%d")
            norm_tgt = self._normalize_time_str(tgt_str, "17:45:00")
            tgt_dt = datetime.strptime(f"{today_str} {norm_tgt}", "%Y-%m-%d %H:%M:%S")
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
        # Tick đã chạy ở update_loop._tick_timer_and_pomodoro — chỉ render UI
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

        if getattr(self, "_last_pomo_btn_running", None) != self.pomo_running:
            self._update_pomo_ctrl_ui()

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
            self.root.geometry(f"{req_w}x{req_h}+{x}+{y}")
            # Config cũ có thể lưu tọa độ màn hình đã tháo → kéo vào desktop ảo
            self.root.after(100, self._clamp_on_screen)
        else:
            cur_w = self.root.winfo_width()
            cur_h = self.root.winfo_height()
            x = self.root.winfo_x()
            y = self.root.winfo_y()
            # CHỈ gọi geometry khi kích thước thực sự thay đổi để tránh Windows DWM composite lại liên tục gây giật giật!
            if cur_w != req_w or cur_h != req_h:
                self.root.geometry(f"{req_w}x{req_h}+{x}+{y}")

    def set_text_color(self, color_hex):
        self.config["text_color"] = color_hex
        self.config["dynamic_time_color"] = False
        self.time_label.configure(fg=color_hex)
        self.save_config()

    def pick_custom_color(self):
        col = None
        try:
            col = colorchooser.askcolor(color=self.config["text_color"], title="Chọn màu chữ")[1]
        finally:
            # askcolor trên Windows hay làm cửa sổ overrideredirect biến mất sau khi đóng
            self.root.after(50, self.ensure_window_visible)
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

    def toggle_windows_autostart(self):
        """Bật/tắt khởi động cùng Windows từ context menu — có feedback khi fail."""
        want = not is_start_with_windows()
        ok = set_start_with_windows(want)
        actual = is_start_with_windows()
        if not ok or actual != want:
            self._safe_messagebox(
                "showerror",
                "Khởi động cùng Windows",
                "Không cập nhật được autostart.\nPath app có thể đã đổi hoặc không ghi được Registry.",
            )
        else:
            self._safe_messagebox(
                "showinfo",
                "Khởi động cùng Windows",
                "Đã bật tự khởi động cùng Windows!" if want else "Đã tắt tự khởi động cùng Windows!",
            )

    def _on_window_mapped(self):
        """Sau deiconify: ẩn taskbar rồi gắn lại click-through (nếu có) cho đúng hit-test."""
        try:
            hide_from_taskbar(self.root)
        except Exception:
            pass
        if getattr(self, "_pending_click_through", False) or self.config.get("click_through", False):
            self.apply_click_through(True)
            self._pending_click_through = False

    def _on_f8_hotkey(self):
        """Hotkey F8 toàn cục — có debounce để không đảo trạng thái 2 lần liên tiếp."""
        now_ts = time.time()
        if now_ts - getattr(self, "_click_through_toggle_ts", 0) < 0.25:
            return
        self.toggle_click_through()

    def toggle_click_through(self):
        self._click_through_toggle_ts = time.time()
        new_val = not self.config.get("click_through", False)
        self.config["click_through"] = new_val

        # Loại trừ tương hỗ: Nếu bật Xuyên chuột thì bắt buộc tắt Tự làm mờ
        if new_val and self.config.get("auto_hide", False):
            self.config["auto_hide"] = False
            self.root.attributes("-alpha", self.config.get("opacity", 0.90))

        ok = self.apply_click_through(new_val)
        # Nếu Win32 không áp được style, rollback config để UI/menu không nói dối
        if not ok:
            self.config["click_through"] = not new_val
            try:
                self.apply_click_through(not new_val)
            except Exception:
                pass
        elif new_val:
            # Đợi hotkey thread đăng ký xong rồi mới cảnh báo (tránh race lúc mới start)
            self.root.after(400, self._warn_if_f8_unavailable)

        self.save_config()

    def _warn_if_f8_unavailable(self):
        """Cảnh báo một lần nếu đang xuyên chuột mà F8 bị app khác chiếm — tránh kẹt không tắt được."""
        if not self.config.get("click_through", False):
            return
        if getattr(self.hotkey_mgr, "f8_registered", False):
            return
        if getattr(self, "_warned_f8_missing", False):
            return
        self._warned_f8_missing = True
        self._safe_messagebox(
            "showwarning",
            "Xuyên chuột",
            "Đã bật xuyên chuột nhưng phím F8 đang bị app khác chiếm.\n"
            "Muốn tắt lại: sửa \"click_through\": false trong file cấu hình rồi mở lại app.",
        )

    def apply_click_through(self, enable):
        try:
            hwnd = self.root.winfo_id()
            ok = set_click_through(hwnd, enable)
            # Giữ alpha (LAYERED); không retry SetWindowPos liên tục — dễ đơ mascot
            self._set_window_alpha(self._full_opacity())
            try:
                self.update_mascot_sprite(force=True)
            except Exception:
                pass
            return bool(ok) or (bool(enable) == is_click_through_active(hwnd))
        except Exception:
            return False

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
        self._is_closing = True
        try:
            self._close_mascot_bubble()
        except Exception:
            pass
        # 1. Ẩn cửa sổ ngay tức thì để không bị đơ trên màn hình
        try:
            self.root.withdraw()
        except Exception:
            pass

        # 2. Lưu lại cấu hình và tọa độ trước khi hủy
        try:
            self.save_config()
        except Exception:
            pass

        # 3. Tắt âm thanh nền và chuông
        try:
            self.focus_sound_mgr.stop()
            sound_mgr.stop_alarm()
        except Exception:
            pass

        # 4. Hủy đăng ký Global Hotkey Win32
        try:
            self.hotkey_mgr.stop()
        except Exception:
            pass

        # 5. Hủy cửa sổ Tkinter
        try:
            self.root.destroy()
        except Exception:
            pass

        # 6. Thoát ngay lập tức (tránh Python runtime bị giật lag khi dọn dẹp các daemon thread)
        os._exit(0)
