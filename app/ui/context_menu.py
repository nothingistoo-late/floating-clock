"""
Context Menu Builder for Top Floating Clock
"""
from datetime import datetime
import tkinter as tk
from app.core.autostart import is_start_with_windows
from app.core.salary_calculator import get_payday_countdown_info
from app.ui.dialogs.weather_dialog import WeatherForecastDialog
from app.ui.youtube_overlay import HOVER_DELAY_PRESETS, LOOP_LABELS, OPACITY_PRESETS, SIZE_PRESETS


class ContextMenuBuilder:
    @staticmethod
    def build(app, parent=None):
        target = parent or app.root
        menu_bg = "#151a24"
        menu_fg = "#f1f5f9"
        active_bg = "#2563eb"
        active_fg = "#ffffff"
        menu_font = ("Segoe UI", 9)

        menu = tk.Menu(
            target,
            tearoff=0,
            bg=menu_bg,
            fg=menu_fg,
            activebackground=active_bg,
            activeforeground=active_fg,
            font=menu_font
        )

        # 1. ⚙️ BẢNG ĐIỀU KHIỂN & CÀI ĐẶT
        menu.add_command(
            label="⚙️  Bảng điều khiển & Cài đặt...",
            font=("Segoe UI", 9, "bold"),
            command=app.open_control_center
        )
        menu.add_separator()

        # 2. 🌟 TIỆN ÍCH & THÔNG TIN HÔM NAY
        now = datetime.now()
        today_dep, today_tag = app.get_today_departure_info(now)
        menu.add_command(
            label=f"🏢  Đếm ngược tan làm ({today_tag}: {today_dep[:5]})",
            command=app.activate_today_departure
        )

        p_days, p_date = get_payday_countdown_info(now, app.config.get("payday_day", 5))
        menu.add_command(
            label=f"💸  Lương Ting Ting: Còn {p_days} ngày ({p_date})",
            command=lambda: app.open_control_center(initial_tab=1)
        )

        sal_cfg = app.config.get("salary", {})
        if sal_cfg.get("enabled", False):
            menu.add_command(
                label="📊  Thống kê chi tiết tiền lương...",
                command=app.open_salary_stats_dialog
            )

        menu.add_command(
            label="🎯  Task trọng tâm hôm nay... [T]",
            command=app.open_quick_task_dialog
        )

        w_data = app.weather_mgr.current_data
        w_city = app.config.get("weather", {}).get("city_name", "")
        if w_data and "temp" in w_data:
            w_icon = w_data.get("icon", "🌤️")
            w_temp = w_data.get("temp", "")
            w_desc = w_data.get("desc", "")
            w_label = f"{w_icon}  Thời tiết: {w_city} ({w_temp}°C • {w_desc}) [W]"
        elif app.weather_mgr.current_weather_str:
            w_label = f"🌦️  {app.weather_mgr.current_weather_str} [W]"
        else:
            w_label = "🌦️  Xem dự báo thời tiết... [W]"

        menu.add_command(
            label=w_label,
            command=app.open_weather_dialog
        )

        # Focus sound submenu
        focus_menu = tk.Menu(menu, tearoff=0, bg=menu_bg, fg=menu_fg, activebackground=active_bg, activeforeground=active_fg, font=menu_font)
        is_snd_playing = app.focus_sound_mgr.is_playing
        cur_snd = app.config.get("focus_sound", {}).get("sound_type", "rain")

        for s_key, s_data in app.focus_sound_mgr.SOUND_TYPES.items():
            pfx = "✓ " if (is_snd_playing and cur_snd == s_key) else "   "
            focus_menu.add_command(
                label=f"{pfx}{s_data['icon']} {s_data['name']}",
                command=lambda k=s_key: app.select_and_play_sound(k)
            )
        focus_menu.add_separator()
        if is_snd_playing:
            focus_menu.add_command(label="⏹ Tắt âm thanh tập trung [F9]", command=lambda: app.toggle_focus_sound())
        else:
            focus_menu.add_command(label="▶ Bật âm thanh tập trung [F9]", command=lambda: app.toggle_focus_sound())

        menu.add_cascade(
            label=f"{'✓ ' if is_snd_playing else '   '}🎧  Âm thanh tập trung (White Noise) [F9]",
            menu=focus_menu
        )

        # YouTube khi hover
        yt = getattr(app, "youtube", None)
        if yt is not None and yt.is_active():
            yt_menu = tk.Menu(menu, tearoff=0, bg=menu_bg, fg=menu_fg, activebackground=active_bg, activeforeground=active_fg, font=menu_font)
            yt_menu.add_command(label="🔗 Đổi link khác... [Ctrl+V]", command=app.open_youtube_link_dialog)
            yt_st = yt.player.status or {}
            if yt.is_playlist():
                yt_count = yt_st.get("playlist_count") or 0
                yt_pos = yt_st.get("playlist_pos")
                pos_txt = f" ({yt_pos + 1}/{yt_count})" if isinstance(yt_pos, int) and yt_count > 1 else ""
                yt_menu.add_command(label=f"⏭ Video tiếp theo{pos_txt}", command=yt.next_video)
                yt_menu.add_command(label="⏮ Video trước", command=yt.prev_video)
            yt_menu.add_command(
                label="↺ Xem lại từ đầu" + (" (đã xem hết)" if yt_st.get("eof") else ""),
                command=yt.replay
            )
            loop_menu_yt = tk.Menu(yt_menu, tearoff=0, bg=menu_bg, fg=menu_fg, activebackground=active_bg, activeforeground=active_fg, font=menu_font)
            cur_loop = app.config.get("youtube", {}).get("loop", "off")
            for loop_key, loop_lbl in LOOP_LABELS:
                pfx = "✓ " if cur_loop == loop_key else "   "
                loop_menu_yt.add_command(label=f"{pfx}{loop_lbl}", command=lambda m=loop_key: yt.set_loop(m))
            yt_menu.add_cascade(label="🔁 Lặp lại", menu=loop_menu_yt)
            yt_menu.add_separator()
            hover_on = app.config.get("youtube", {}).get("hover_enabled", True)
            yt_menu.add_command(
                label=f"{'✓ ' if hover_on else '   '}Hiện video khi rê chuột",
                command=app.toggle_youtube_hover
            )
            delay_menu_yt = tk.Menu(yt_menu, tearoff=0, bg=menu_bg, fg=menu_fg, activebackground=active_bg, activeforeground=active_fg, font=menu_font)
            cur_delay = yt.get_hover_delay()
            for d_sec in HOVER_DELAY_PRESETS:
                pfx = "✓ " if abs(cur_delay - d_sec) < 0.05 else "   "
                delay_menu_yt.add_command(
                    label=f"{pfx}{d_sec:g} giây",
                    command=lambda v=d_sec: yt.set_hover_delay(v)
                )
            yt_menu.add_cascade(label=f"⏱ Giữ chuột bao lâu mới hiện video (đang {cur_delay:g}s)", menu=delay_menu_yt)

            # Kích thước khung video
            size_menu_yt = tk.Menu(yt_menu, tearoff=0, bg=menu_bg, fg=menu_fg, activebackground=active_bg, activeforeground=active_fg, font=menu_font)
            cur_w = int(app.config.get("youtube", {}).get("width", 480))
            for sz_name, sz_w in SIZE_PRESETS:
                pfx = "✓ " if abs(cur_w - sz_w) < 20 else "   "
                size_menu_yt.add_command(
                    label=f"{pfx}{sz_name} ({sz_w}×{sz_w * 9 // 16})",
                    command=lambda w=sz_w: app.youtube.set_width(w)
                )
            yt_menu.add_cascade(label=f"📐 Kích thước video (đang {cur_w}px)", menu=size_menu_yt)

            # Độ mờ khung video khi hiện
            op_menu_yt = tk.Menu(yt_menu, tearoff=0, bg=menu_bg, fg=menu_fg, activebackground=active_bg, activeforeground=active_fg, font=menu_font)
            cur_op = app.youtube.get_opacity()
            for op in OPACITY_PRESETS:
                pfx = "✓ " if abs(cur_op - op) < 0.03 else "   "
                op_lbl = "Rõ hẳn" if op >= 1.0 else f"Mờ {int(round((1 - op) * 100))}%"
                op_menu_yt.add_command(
                    label=f"{pfx}{int(op * 100)}% ({op_lbl})",
                    command=lambda v=op: app.youtube.set_opacity(v)
                )
            yt_menu.add_cascade(label=f"🌫️ Độ mờ video (đang {int(cur_op * 100)}%)", menu=op_menu_yt)

            yt_menu.add_separator()
            yt_menu.add_command(label="⏹ Tắt video YouTube", command=app.stop_youtube)
            menu.add_cascade(label="✓ 📺  YouTube đang mở (rê chuột để xem)", menu=yt_menu)
        else:
            menu.add_command(
                label="📺  Xem YouTube khi rê chuột... [Ctrl+V]",
                command=app.open_youtube_link_dialog
            )

        menu.add_command(
            label="💬  Đổi câu động viên GenZ mới 🎲",
            command=app.request_next_quote
        )
        menu.add_separator()

        # 3. 🔄 CHẾ ĐỘ & BỘ ĐẾM GIỜ
        mode_menu = tk.Menu(menu, tearoff=0, bg=menu_bg, fg=menu_fg, activebackground=active_bg, activeforeground=active_fg, font=menu_font)
        modes = [
            ("🕒 Đồng hồ thời gian thực", "clock"),
            ("🎯 Đến thời gian / Tan làm", "target_time"),
            ("⏳ Đếm ngược (Countdown Timer)", "timer"),
            ("⏱️ Bấm giờ thể thao (Stopwatch)", "stopwatch"),
            ("🍅 Pomodoro (Làm việc tập trung)", "pomodoro"),
        ]
        for label, m in modes:
            prefix = "✓ " if app.current_mode == m else "   "
            mode_menu.add_command(label=f"{prefix}{label}", command=lambda mode_name=m: app.switch_mode(mode_name))
        menu.add_cascade(label="🔄  Chế độ hoạt động [F2]", menu=mode_menu)

        timer_sub = tk.Menu(menu, tearoff=0, bg=menu_bg, fg=menu_fg, activebackground=active_bg, activeforeground=active_fg, font=menu_font)
        for name, sec in [("1 Phút", 60), ("3 Phút", 180), ("5 Phút", 300), ("10 Phút", 600), ("15 Phút", 900), ("25 Phút", 1500), ("30 Phút", 1800), ("1 Giờ", 3600)]:
            timer_sub.add_command(label=name, command=lambda s=sec: app.start_quick_timer(s))
        menu.add_cascade(label="⏳  Đặt nhanh đếm ngược", menu=timer_sub)
        menu.add_separator()

        # 4. ⚡ BẬT / TẮT NHANH
        is_mini = app.config.get("mini_mode", False)
        menu.add_command(
            label=f"{'✓ ' if is_mini else '   '}🔍  Chế độ thu nhỏ tối giản [M]",
            command=app.toggle_mini_mode
        )

        is_dyn = app.config.get("dynamic_time_color", True)
        menu.add_command(
            label=f"{'✓ ' if is_dyn else '   '}🌈  Đổi màu động theo thời gian [D]",
            command=app.toggle_dynamic_color
        )

        is_hid_sal = app.config.get("salary", {}).get("hidden", False)
        menu.add_command(
            label=f"{'✓ ' if is_hid_sal else '   '}🔒  Ẩn / Che số tiền lương [S]",
            command=app.toggle_salary_hide
        )

        is_autohide = app.config.get("auto_hide", False)
        menu.add_command(
            label=f"{'✓ ' if is_autohide else '   '}🧲  Tự làm mờ khi rời chuột [H]",
            command=app.toggle_autohide
        )

        is_mascot = app.config.get("show_mascot", True)
        menu.add_command(
            label=f"{'✓ ' if is_mascot else '   '}🐱  Thú cưng Pixel Cat [P]",
            command=app.toggle_mascot
        )

        if is_mascot:
            mascot_action_menu = tk.Menu(menu, tearoff=0, bg=menu_bg, fg=menu_fg, activebackground=active_bg, activeforeground=active_fg, font=menu_font)
            cur_act = app.config.get("mascot_action", "auto")
            acts = [
                ("🔄 Tự động (Theo giờ & Pomodoro)", "auto"),
                ("🧘 Thư giãn (Luôn Idle)", "idle"),
                ("💻 Gõ phím làm việc (Luôn Working)", "work"),
                ("🎒 Nhảy nhót ăn mừng (Luôn Happy)", "leaving"),
                ("💤 Ngủ say sưa (Luôn Sleeping)", "sleep"),
            ]
            for act_lbl, act_val in acts:
                pfx = "✓ " if cur_act == act_val else "   "
                mascot_action_menu.add_command(label=f"{pfx}{act_lbl}", command=lambda v=act_val: app.set_mascot_action(v))
            menu.add_cascade(label="   🐾  Hành động của thú cưng", menu=mascot_action_menu)
        menu.add_separator()

        # 5. 🎨 GIAO DIỆN & VỊ TRÍ
        color_menu = tk.Menu(menu, tearoff=0, bg=menu_bg, fg=menu_fg, activebackground=active_bg, activeforeground=active_fg, font=menu_font)
        colors = [
            ("Cyan Neon (Xanh ngọc)", "#00FFCC"),
            ("Lime Green (Xanh lá)", "#10B981"),
            ("Amber Gold (Vàng cam)", "#F59E0B"),
            ("Pink Neon (Hồng tím)", "#EC4899"),
            ("Sky Blue (Xanh dương)", "#38BDF8"),
            ("Violet (Tím)", "#A855F7"),
            ("Pure White (Trắng)", "#FFFFFF"),
            ("Fire Red (Đỏ)", "#EF4444"),
        ]
        for name, col in colors:
            pfx = "✓ " if app.config.get("text_color") == col else "   "
            color_menu.add_command(label=f"{pfx}{name}", command=lambda c=col: app.set_text_color(c))
        color_menu.add_separator()
        color_menu.add_command(label="🎨 Màu tùy chọn...", command=app.pick_custom_color)
        menu.add_cascade(label="🎨  Đổi màu chữ cố định", menu=color_menu)

        opacity_menu = tk.Menu(menu, tearoff=0, bg=menu_bg, fg=menu_fg, activebackground=active_bg, activeforeground=active_fg, font=menu_font)
        for val in [1.0, 0.9, 0.75, 0.6, 0.4]:
            pfx = "✓ " if abs(app.config.get("opacity", 0.9) - val) < 0.05 else "   "
            opacity_menu.add_command(label=f"{pfx}{int(val * 100)}%", command=lambda v=val: app.set_opacity(v))
        menu.add_cascade(label="🌫️  Độ trong suốt (Opacity)", menu=opacity_menu)

        size_menu = tk.Menu(menu, tearoff=0, bg=menu_bg, fg=menu_fg, activebackground=active_bg, activeforeground=active_fg, font=menu_font)
        for sz in [14, 16, 18, 20, 24, 28, 32, 38]:
            pfx = "✓ " if app.config.get("font_size") == sz else "   "
            size_menu.add_command(label=f"{pfx}Cỡ {sz}px", command=lambda s=sz: app.set_font_size(s))
        menu.add_cascade(label="🔤  Kích thước chữ", menu=size_menu)

        pos_menu = tk.Menu(menu, tearoff=0, bg=menu_bg, fg=menu_fg, activebackground=active_bg, activeforeground=active_fg, font=menu_font)
        pos_menu.add_command(label="Đỉnh giữa (Top Center)", command=app.reset_to_top_center)
        pos_menu.add_command(label="Đỉnh phải (Top Right)", command=app.reset_to_top_right)
        pos_menu.add_command(label="Đỉnh trái (Top Left)", command=app.reset_to_top_left)
        pos_menu.add_command(label="Đáy giữa (Bottom Center)", command=app.reset_to_bottom_center)
        menu.add_cascade(label="📍  Căn vị trí nhanh", menu=pos_menu)
        menu.add_separator()

        # 6. 💻 HỆ THỐNG & CỬA SỔ
        is_autostart = is_start_with_windows()
        menu.add_command(
            label=f"{'✓ ' if is_autostart else '   '}🚀  Khởi động cùng Windows",
            command=app.toggle_windows_autostart
        )

        menu.add_command(
            label=f"{'✓ ' if app.config['locked'] else '   '}🔒  Khóa vị trí (Chống kéo nhầm)",
            command=app.toggle_lock
        )

        menu.add_command(
            label=f"{'✓ ' if app.config['click_through'] else '   '}🖱️  Xuyên chuột [F8]",
            command=app.toggle_click_through
        )
        menu.add_command(
            label="🔄  Kiểm tra bản cập nhật...",
            command=lambda: app.check_for_updates(interactive=True)
        )
        menu.add_separator()

        # 7. ❌ ĐÓNG ỨNG DỤNG
        menu.add_command(
            label="❌  Đóng ứng dụng",
            font=("Segoe UI", 9, "bold"),
            command=app.quit_app
        )

        return menu
