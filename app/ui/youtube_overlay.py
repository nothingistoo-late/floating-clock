"""
YouTube Hover Overlay — popup video nằm đè lên đồng hồ.

- Giữ chuột trên đồng hồ (mặc định 3s, viền nháy đỏ báo hiệu) → popup video hiện ra + phát tiếp.
- Rê chuột ra ngoài (~0.35s) → popup ẩn đi + TẠM DỪNG video, đồng hồ hiện lại như bình thường.
- Thanh điều khiển kiểu YouTube luôn hiện dưới video (xem youtube_controls.py).
- Popup hiện / ẩn bằng SetWindowPos + SWP_NOACTIVATE (đỗ ra ngoài màn hình khi ẩn)
  → KHÔNG cướp focus bàn phím của app bạn đang làm việc.
- Phát hiện hover bằng polling vị trí con trỏ: cửa sổ mpv con "nuốt" sự kiện chuột nên
  không dựa vào <Enter>/<Leave> của Tk được.
"""
import time
import tkinter as tk

from app.core.win32_utils import (
    get_monitor_work_area,
    get_virtual_screen_rect,
    hide_from_taskbar,
    is_any_mouse_button_down,
    is_left_mouse_down,
    move_window_noactivate,
    raise_topmost_noactivate,
)
from app.services.youtube_player import SPEED_PRESETS, YouTubePlayer, parse_youtube_url
from app.ui.youtube_controls import YouTubeControlBar

MENU_STYLE = dict(tearoff=0, bg="#151a24", fg="#f1f5f9", activebackground="#2563eb",
                  activeforeground="#ffffff", font=("Segoe UI", 9))

QUALITY_LABELS = [
    ("1080", "1080p (nét nhất, tốn CPU)"),
    ("720", "720p (mặc định)"),
    ("480", "480p"),
    ("360", "360p (nhẹ máy, tiết kiệm mạng)"),
]

DEFAULT_YOUTUBE_CFG = {
    "last_url": "",
    "width": 480,
    "volume": 70,
    "hover_enabled": True,
    "opacity": 1.0,             # độ đậm của khung video khi hiện (1.0 = rõ hẳn, 0.4 = mờ nhiều)
    "loop": "off",              # "off" hết thì dừng | "one" lặp 1 video | "all" lặp cả danh sách
    "hover_delay_sec": 3.0,     # giữ chuột trên đồng hồ bao lâu mới chuyển sang video
    "quality": "720",           # "1080" | "720" | "480" | "360"
    "speed": 1.0,               # tốc độ phát (giữ cho các video sau như YouTube)
}

# Thời gian chờ chọn nhanh (giây)
HOVER_DELAY_PRESETS = [1.0, 2.0, 3.0, 5.0]

LOOP_LABELS = [
    ("off", "Tắt (hết thì dừng ở khung cuối)"),
    ("one", "Lặp lại video đang xem"),
    ("all", "Lặp lại cả danh sách"),
]

# Kích thước chọn nhanh (bề rộng px, cao tự theo 16:9)
SIZE_PRESETS = [
    ("Nhỏ", 360),
    ("Vừa", 480),
    ("Lớn", 640),
    ("Rất lớn", 854),
    ("Khổng lồ", 1024),
]
OPACITY_PRESETS = [1.0, 0.85, 0.7, 0.55, 0.4]
MIN_WIDTH = 320
MAX_WIDTH = 1600


class YouTubeOverlay:
    """Quản lý popup video YouTube + máy trạng thái hover. Chủ sở hữu: FloatingClock."""

    BAR_H = 26
    CTRL_H = YouTubeControlBar.HEIGHT
    LEAVE_HIDE_DELAY = 0.35     # giây chuột ở ngoài trước khi ẩn (tránh nhấp nháy ở mép)
    TICK_MS = 80
    EARLY_EXIT_SEC = 20         # mpv thoát trong khoảng này sau khi mở → coi là lỗi phát

    def __init__(self, app):
        self.app = app
        self.player = YouTubePlayer()
        self.win = None
        self.video_frame = None
        self.title_label = None
        self.shown = False
        self._rect = (0, 0, 0, 0)
        self._hover_since = None
        self._away_since = None
        self._tick_id = None
        self._last_raise = 0.0
        self._started_at = 0.0
        self._resize_start = None   # (pointer_x, width) lúc bắt đầu kéo góc resize
        # Trạng thái nhấp nháy viền báo hiệu
        self._blink_hover_ref = None
        self._blink_phase = 0.0
        self._blink_last_ts = 0.0
        # Thanh điều khiển & trạng thái "người dùng tự bấm dừng" (khi đó hover vào không tự phát tiếp)
        self.controls = None
        self._user_paused = False
        self._transition_ts = 0.0   # lúc vừa hiện/ẩn — trạng thái pause đọc từ mpv chưa kịp cập nhật
        self._menu_open_since = None

    # ---------------- Cấu hình ----------------
    @property
    def cfg(self):
        yt = self.app.config.setdefault("youtube", {})
        for k, v in DEFAULT_YOUTUBE_CFG.items():
            yt.setdefault(k, v)
        return yt

    def is_active(self):
        return self.player.is_running()

    # ---------------- API cho app ----------------
    def play_url(self, raw_url):
        """Phát link YouTube. Trả (ok: bool, message: str)."""
        info = parse_youtube_url(raw_url)
        if not info:
            return False, "Link này không phải video YouTube hợp lệ (・_・;)"
        if not self.player.is_available():
            return False, (
                "Chưa tìm thấy mpv.exe nên chưa phát video được.\n\n"
                "Cách cài: tải bản mpv cho Windows, chép mpv.exe vào thư mục app\\bin "
                "(cạnh yt-dlp.exe) hoặc cài mpv vào PATH, rồi dán link lại nhé (◕‿◕)"
            )

        self._ensure_window()
        self._show()  # hiện trước để mpv có khung vẽ đúng kích thước
        try:
            self.win.update_idletasks()
            self.player.play(
                info, self.video_frame.winfo_id(),
                volume=self.cfg.get("volume", 70), loop=self.cfg.get("loop", "off"),
                quality=self.cfg.get("quality", "720"), speed=self.cfg.get("speed", 1.0),
            )
        except Exception as e:
            self._teardown_window()
            return False, f"Không mở được trình phát: {e}"

        self._started_at = time.time()
        self._user_paused = False
        self.cfg["last_url"] = info["url"]
        self._update_title()
        self.app.save_config()
        self._schedule_tick()
        return True, ""

    def stop(self):
        """Tắt hẳn video và đóng popup."""
        self._cancel_tick()
        self.player.stop()
        self._teardown_window()

    # ---------------- Báo hiệu sắp chuyển sang video ----------------
    BLINK_ON = "#EF4444"        # đỏ YouTube
    BLINK_OFF = "#7F1D1D"       # đỏ sẫm

    def hover_progress(self):
        """
        Đang giữ chuột chờ hiện video → tiến độ 0..1; không chờ (chưa mở video, đang hiện, đã rời chuột) → None.
        Đồng hồ dùng giá trị này để nhấp nháy viền báo hiệu.
        """
        if self.shown or self._hover_since is None or not self.player.is_running():
            return None
        return max(0.0, min(1.0, (time.time() - self._hover_since) / self.get_hover_delay()))

    def blink_color(self, progress):
        """
        Màu viền theo thời điểm: chu kỳ nháy rút từ ~0.9s xuống ~0.24s khi tiến độ tiến tới 1.
        (Vòng lặp vẽ chạy ~20 lần/s nên không nháy nhanh hơn mức này kẻo mắt không phân biệt được.)
        """
        half_period = 0.45 - 0.33 * max(0.0, min(1.0, progress))
        now = time.time()
        # Cộng dồn pha theo thời gian thực trôi qua (chia thẳng time.time() cho chu kỳ đang đổi
        # sẽ nhảy pha loạn xạ vì time.time() rất lớn). Bắt đầu lượt hover mới → pha về 0 (sáng trước).
        if self._blink_hover_ref != self._hover_since:
            self._blink_hover_ref = self._hover_since
            self._blink_phase = 0.0
            self._blink_last_ts = now
        self._blink_phase += max(0.0, now - self._blink_last_ts) / half_period
        self._blink_last_ts = now
        return self.BLINK_ON if int(self._blink_phase) % 2 == 0 else self.BLINK_OFF

    def get_hover_delay(self):
        try:
            return max(0.2, min(10.0, float(self.cfg.get("hover_delay_sec", 3.0))))
        except Exception:
            return 3.0

    def set_hover_delay(self, seconds):
        self.cfg["hover_delay_sec"] = max(0.2, min(10.0, float(seconds)))
        self._hover_since = None
        self.app.save_config()

    def get_opacity(self):
        try:
            return max(0.2, min(1.0, float(self.cfg.get("opacity", 1.0))))
        except Exception:
            return 1.0

    def set_opacity(self, value):
        """Đổi độ mờ khung video (áp dụng ngay nếu đang mở)."""
        self.cfg["opacity"] = max(0.2, min(1.0, float(value)))
        self._apply_opacity()
        self.app.save_config()

    def set_width(self, width):
        """Đổi bề rộng khung video (cao tự theo 16:9), áp dụng ngay nếu đang hiện."""
        self.cfg["width"] = max(MIN_WIDTH, min(MAX_WIDTH, int(width)))
        self._reposition_if_shown()
        self.app.save_config()

    def _apply_opacity(self):
        if self.win is None:
            return
        try:
            self.win.attributes("-alpha", self.get_opacity())
        except Exception:
            pass

    def _reposition_if_shown(self):
        if self.shown and self.win is not None:
            x, y, w, h = self._target_rect()
            move_window_noactivate(self.win, x, y, w, h, topmost=True)
            self._rect = (x, y, w, h)

    # ---------------- Playlist / hết video ----------------
    def is_playlist(self):
        cur = self.player.current or {}
        return bool(cur.get("list")) or (self.player.status.get("playlist_count") or 0) > 1

    def next_video(self):
        self.player.next()

    def prev_video(self):
        self.player.prev()

    def replay(self):
        self.player.replay()

    def set_loop(self, mode):
        self.cfg["loop"] = mode
        self.player.set_loop(mode)
        self.app.save_config()

    # ---------------- Thanh điều khiển (gọi từ YouTubeControlBar) ----------------
    def toggle_pause(self):
        st = self.player.status or {}
        if st.get("eof"):
            self.player.replay()
            self._user_paused = False
        elif st.get("paused"):
            self.player.resume()
            self._user_paused = False
        else:
            self.player.pause()
            self._user_paused = True
        self._transition_ts = time.time()

    def seek_fraction(self, fraction):
        dur = (self.player.status or {}).get("duration")
        if isinstance(dur, (int, float)) and dur > 0:
            self.player.seek_to(fraction * dur)

    def on_volume_drag(self, fraction):
        vol = int(round(fraction * 100))
        self.player.set_volume(vol)
        if vol > 0:
            self.player.set_mute(False)

    def on_volume_release(self, fraction):
        self.on_volume_drag(fraction)
        self.cfg["volume"] = int(round(fraction * 100))
        self.app.save_config()

    def nudge_volume(self, delta):
        cur = (self.player.status or {}).get("volume")
        cur = cur if isinstance(cur, (int, float)) else self.cfg.get("volume", 70)
        new = max(0, min(100, int(cur) + delta))
        self.player.set_volume(new)
        self.cfg["volume"] = new
        if self.controls:
            self.controls.vol.set_fraction(new / 100.0)
        self.app.save_config()

    def toggle_mute(self):
        self.player.set_mute(not bool((self.player.status or {}).get("mute")))

    def set_speed(self, speed):
        self.cfg["speed"] = float(speed)
        self.player.set_speed(speed)
        self.app.save_config()

    def set_quality(self, quality):
        self.cfg["quality"] = str(quality)
        self.player.set_quality(quality)
        self.app.save_config()

    def _post_menu(self, menu, anchor_widget):
        """Mở menu ngay trên nút bấm; trong lúc menu mở thì không ẩn video."""
        self._menu_open_since = time.time()
        try:
            x = anchor_widget.winfo_rootx()
            y = anchor_widget.winfo_rooty()
            # Trên Windows tk_popup CHẶN tới khi menu đóng (vòng hover vẫn chạy nhờ timer của Tk),
            # còn <Unmap> của menu không bắn → đánh dấu đóng ngay khi tk_popup trả về
            menu.tk_popup(x, y - 4)
        finally:
            self._menu_open_since = None
            try:
                menu.grab_release()
            except Exception:
                pass

    def _add_speed_items(self, menu):
        cur = float(self.cfg.get("speed", 1.0))
        for spd in SPEED_PRESETS:
            pfx = "✓ " if abs(cur - spd) < 0.01 else "   "
            lbl = "Bình thường" if spd == 1.0 else f"{spd:g}x"
            menu.add_command(label=f"{pfx}{lbl}", command=lambda v=spd: self.set_speed(v))

    def open_speed_menu(self, anchor_widget):
        menu = tk.Menu(self.win, **MENU_STYLE)
        menu.add_command(label="Tốc độ phát", state="disabled")
        self._add_speed_items(menu)
        self._post_menu(menu, anchor_widget)

    def open_settings_menu(self, anchor_widget):
        """⚙ giống YouTube: chất lượng, tốc độ, lặp lại + kích thước, độ mờ của khung."""
        menu = tk.Menu(self.win, **MENU_STYLE)

        q_menu = tk.Menu(menu, **MENU_STYLE)
        cur_q = str(self.cfg.get("quality", "720"))
        for q_key, q_lbl in QUALITY_LABELS:
            pfx = "✓ " if cur_q == q_key else "   "
            q_menu.add_command(label=f"{pfx}{q_lbl}", command=lambda v=q_key: self.set_quality(v))
        menu.add_cascade(label=f"🎞 Chất lượng ({cur_q}p)", menu=q_menu)

        s_menu = tk.Menu(menu, **MENU_STYLE)
        self._add_speed_items(s_menu)
        menu.add_cascade(label=f"⏩ Tốc độ ({float(self.cfg.get('speed', 1.0)):g}x)", menu=s_menu)

        l_menu = tk.Menu(menu, **MENU_STYLE)
        cur_loop = self.cfg.get("loop", "off")
        for l_key, l_lbl in LOOP_LABELS:
            pfx = "✓ " if cur_loop == l_key else "   "
            l_menu.add_command(label=f"{pfx}{l_lbl}", command=lambda m=l_key: self.set_loop(m))
        menu.add_cascade(label="🔁 Lặp lại", menu=l_menu)
        menu.add_separator()

        z_menu = tk.Menu(menu, **MENU_STYLE)
        cur_w = int(self.cfg.get("width", 480))
        for z_name, z_w in SIZE_PRESETS:
            pfx = "✓ " if abs(cur_w - z_w) < 20 else "   "
            z_menu.add_command(label=f"{pfx}{z_name} ({z_w}×{z_w * 9 // 16})",
                               command=lambda w=z_w: self.set_width(w))
        menu.add_cascade(label=f"📐 Kích thước khung ({cur_w}px)", menu=z_menu)

        o_menu = tk.Menu(menu, **MENU_STYLE)
        cur_op = self.get_opacity()
        for op in OPACITY_PRESETS:
            pfx = "✓ " if abs(cur_op - op) < 0.03 else "   "
            o_menu.add_command(label=f"{pfx}{int(op * 100)}%", command=lambda v=op: self.set_opacity(v))
        menu.add_cascade(label=f"🌫️ Độ mờ khung ({int(cur_op * 100)}%)", menu=o_menu)
        self._post_menu(menu, anchor_widget)

    def toggle_hover_enabled(self):
        self.cfg["hover_enabled"] = not self.cfg.get("hover_enabled", True)
        if not self.cfg["hover_enabled"] and self.shown:
            self._hide()
        self.app.save_config()

    def shutdown(self):
        """Gọi khi thoát app."""
        try:
            self._cancel_tick()
            self.player.stop()
        except Exception:
            pass

    # ---------------- Cửa sổ popup ----------------
    def _ensure_window(self):
        if self.win is not None:
            try:
                if self.win.winfo_exists():
                    return
            except Exception:
                pass

        win = tk.Toplevel(self.app.root)
        win.withdraw()
        try:
            win.attributes("-toolwindow", True)
        except Exception:
            pass
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.configure(bg="#000000")

        bar = tk.Frame(win, bg="#11141c", height=self.BAR_H, cursor="fleur")
        bar.pack(fill="x", side="top")
        bar.pack_propagate(False)

        self.title_label = tk.Label(
            bar, text="📺 YouTube", font=("Segoe UI", 8, "bold"),
            bg="#11141c", fg="#F87171", anchor="w"
        )
        self.title_label.pack(side="left", padx=(8, 4), fill="x", expand=True)

        btn_style = dict(font=("Segoe UI", 9, "bold"), bg="#11141c", fg="#CBD5E1",
                         activebackground="#334155", activeforeground="#FFFFFF",
                         relief="flat", bd=0, padx=8, cursor="hand2")
        tk.Button(bar, text="✕", command=self.app.stop_youtube, **btn_style).pack(side="right")
        hint_label = tk.Label(
            bar, text="lăn chuột: đổi cỡ • rời chuột: tạm dừng", font=("Segoe UI", 7),
            bg="#11141c", fg="#64748B", cursor="fleur"
        )
        hint_label.pack(side="right", padx=(0, 4))

        # Thanh tiêu đề: kéo để dời cả đồng hồ lẫn video, lăn chuột đổi cỡ, chuột phải mở menu.
        # Gắn cho MỌI phần của thanh (trừ nút ✕) — bấm trúng dòng chữ nào cũng kéo được.
        self.title_label.configure(cursor="fleur")
        for w in (bar, self.title_label, hint_label):
            w.bind("<ButtonPress-1>", self._on_bar_press)
            w.bind("<B1-Motion>", self._on_bar_drag)
            w.bind("<ButtonRelease-1>", self._on_bar_release)
            w.bind("<Button-3>", self.app.show_context_menu)
            w.bind("<MouseWheel>", self._on_bar_wheel)

        # Thanh điều khiển kiểu YouTube (pack trước video để luôn giữ chỗ ở đáy)
        self.controls = YouTubeControlBar(win, self)
        self.controls.pack(fill="x", side="bottom")

        self.video_frame = tk.Frame(win, bg="#000000")
        self.video_frame.pack(fill="both", expand=True)

        # Góc kéo resize nằm cuối thanh điều khiển (không đè lên video), giữ tỉ lệ 16:9
        grip = self.controls.grip
        grip.bind("<ButtonPress-1>", self._on_grip_press)
        grip.bind("<B1-Motion>", self._on_grip_drag)
        grip.bind("<ButtonRelease-1>", self._on_grip_release)
        self.grip = grip

        self.win = win
        self._apply_opacity()
        # Map 1 lần lúc tạo (người dùng đang thao tác dán link nên chấp nhận được),
        # từ đó về sau chỉ dời vị trí bằng SWP_NOACTIVATE → không cướp focus nữa
        win.deiconify()
        hide_from_taskbar(win)
        self._park_offscreen()

    def _teardown_window(self):
        self.shown = False
        self._hover_since = None
        self._away_since = None
        if self.win is not None:
            try:
                self.win.destroy()
            except Exception:
                pass
        self.win = None
        self.video_frame = None
        self.title_label = None
        self.grip = None
        self.controls = None
        self._menu_open_since = None
        self._resize_start = None
        self._set_clock_hidden(False)
        # Bug Tk overrideredirect trên Windows: hủy Toplevel con có thể làm mất đồng hồ → kéo lại
        try:
            self.app.root.after(50, self.app.ensure_window_visible)
        except Exception:
            pass

    def _title_text(self):
        """Dòng tiêu đề: thứ tự trong danh sách + tên video, hoặc trạng thái tải / đã xem hết."""
        st = self.player.status or {}
        cur = self.player.current or {}
        title = st.get("title") or ""
        count = st.get("playlist_count") or 0
        pos = st.get("playlist_pos")
        # media-title = URL nghĩa là yt-dlp còn đang lấy thông tin
        loading = (not title) or title.startswith("http") or "youtube.com" in title
        if loading:
            return "⏳ Đang tải danh sách phát..." if cur.get("list") else "⏳ Đang tải video..."

        prefix = "📺"
        if count > 1 and isinstance(pos, int) and pos >= 0:
            prefix = f"📺 {pos + 1}/{count}"
        if st.get("eof"):
            prefix = "✅ Đã xem hết" + (f" ({count} video)" if count > 1 else "") + " •"
        text = f"{prefix} {title}"
        # Cắt theo bề rộng khung (chừa chỗ cho dòng gợi ý + nút ✕)
        max_chars = max(14, int((self._rect[2] or 480) / 7.5) - 34)
        return text if len(text) <= max_chars else text[: max_chars - 1] + "…"

    def _update_title(self):
        if not self.title_label:
            return
        txt = self._title_text()
        if self.title_label.cget("text") != txt:
            self.title_label.configure(text=txt)

    def _target_rect(self):
        """Popup neo ở góc trên trái đồng hồ, đúng bề rộng người dùng chọn, luôn nằm trọn trong màn hình."""
        root = self.app.root
        cx, cy = root.winfo_rootx(), root.winfo_rooty()
        cw, ch = max(1, root.winfo_width()), max(1, root.winfo_height())
        try:
            base_w = int(self.cfg.get("width", 480))
        except Exception:
            base_w = 480
        left, top, right, bottom = get_monitor_work_area(cx + cw // 2, cy + ch // 2)
        vw = max(MIN_WIDTH, min(base_w, right - left, MAX_WIDTH))
        chrome_h = self.BAR_H + self.CTRL_H   # thanh tiêu đề + thanh điều khiển
        vh = int(vw * 9 / 16) + chrome_h
        if vh > bottom - top:
            vh = bottom - top
            vw = int((vh - chrome_h) * 16 / 9)
        x = min(max(cx, left), right - vw)
        y = min(max(cy, top), bottom - vh)
        return int(x), int(y), int(vw), int(vh)

    def _show(self):
        if self.win is None:
            return
        x, y, w, h = self._target_rect()
        move_window_noactivate(self.win, x, y, w, h, topmost=True)
        self._rect = (x, y, w, h)
        self.shown = True
        self._away_since = None
        self._last_raise = time.time()
        self._transition_ts = time.time()
        # Người dùng đã tự bấm dừng (nút ⏸ / click video) hoặc đã xem hết → hiện lại nhưng KHÔNG tự phát
        if not self._user_paused and not (self.player.status or {}).get("eof"):
            self.player.resume()
        # Chỉ hiện 1 thứ: video lên thì đồng hồ tàng hình
        self._set_clock_hidden(True)

    def _hide(self):
        self.player.pause()
        self._transition_ts = time.time()
        self._park_offscreen()
        self.shown = False
        self._hover_since = None
        # Đồng hồ hiện lại như bình thường
        self._set_clock_hidden(False)

    def _park_offscreen(self):
        """Ẩn bằng cách đỗ popup ra ngoài mọi màn hình (không withdraw → không cướp focus khi hiện lại)."""
        if self.win is None:
            return
        vx, vy, _vw, _vh = get_virtual_screen_rect()
        _, _, w, h = self._rect if self._rect[2] > 0 else (0, 0, 480, 296)
        move_window_noactivate(self.win, vx - w - 4000, vy, w, h, topmost=True)

    def _set_clock_hidden(self, hidden):
        fn_name = "hide_clock_for_video" if hidden else "restore_clock_after_video"
        fn = getattr(self.app, fn_name, None)
        if fn:
            try:
                fn()
            except Exception:
                pass

    # ---------------- Kéo thả thanh tiêu đề ----------------
    def _on_bar_press(self, event):
        self.app.start_drag(event)
        return "break"

    def _on_bar_drag(self, event):
        self.app.do_drag(event)
        self._follow_clock()
        return "break"

    def _on_bar_release(self, event):
        self.app.stop_drag(event)
        self._follow_clock()
        return "break"

    def _follow_clock(self):
        """Dời popup theo đồng hồ. Phải áp geometry mới của đồng hồ trước khi đọc tọa độ (không thì lệch 1 nhịp)."""
        try:
            self.app.root.update_idletasks()
        except Exception:
            pass
        self._reposition_if_shown()

    # ---------------- Resize ----------------
    def _on_grip_press(self, event):
        self._resize_start = (event.x_root, self._rect[2] if self._rect[2] > 0 else int(self.cfg.get("width", 480)))
        return "break"

    def _on_grip_drag(self, event):
        if not self._resize_start:
            return "break"
        start_x, start_w = self._resize_start
        new_w = max(MIN_WIDTH, min(MAX_WIDTH, start_w + (event.x_root - start_x)))
        self.cfg["width"] = int(new_w)
        self._reposition_if_shown()
        return "break"

    def _on_grip_release(self, event):
        if self._resize_start:
            self._resize_start = None
            self.app.save_config()
        return "break"

    def _on_bar_wheel(self, event):
        """Lăn lên → to ra, lăn xuống → nhỏ lại (mỗi nấc 40px)."""
        step = 40 if event.delta > 0 else -40
        cur = self._rect[2] if self._rect[2] > 0 else int(self.cfg.get("width", 480))
        self.set_width(cur + step)
        return "break"

    # ---------------- Vòng lặp hover ----------------
    def _schedule_tick(self):
        self._cancel_tick()
        try:
            self._tick_id = self.app.root.after(self.TICK_MS, self._tick)
        except Exception:
            self._tick_id = None

    def _cancel_tick(self):
        if self._tick_id is not None:
            try:
                self.app.root.after_cancel(self._tick_id)
            except Exception:
                pass
        self._tick_id = None

    @staticmethod
    def _point_in(rect, px, py):
        x, y, w, h = rect
        return w > 0 and h > 0 and x <= px < x + w and y <= py < y + h

    def _tick(self):
        self._tick_id = None
        if getattr(self.app, "_is_closing", False):
            return

        if not self.player.is_running():
            self._on_player_exited()
            return

        now = time.time()
        try:
            px, py = self.app.root.winfo_pointerxy()
        except Exception:
            px, py = -99999, -99999
        over_clock = self.app._pointer_over_clock()
        self._update_title()
        # Menu ⚙ / tốc độ của popup đang mở (có hạn 60s phòng sự kiện đóng menu bị lỡ)
        own_menu = self._menu_open_since is not None and now - self._menu_open_since < 60
        menu_open = bool(getattr(self.app, "_is_menu_open", False)) or own_menu

        if self.shown:
            st = self.player.status or {}
            if self.controls is not None:
                try:
                    self.controls.refresh(st, self.is_playlist())
                except Exception:
                    pass
            # Ghi nhận người dùng tự dừng / phát (click vào video) — bỏ qua lúc vừa hiện/ẩn vì trạng thái còn cũ
            if now - self._transition_ts > 1.5 and "paused" in st and not st.get("eof"):
                self._user_paused = bool(st.get("paused"))

            keep = (
                self._point_in(self._rect, px, py)
                or over_clock
                or menu_open
                or is_left_mouse_down()   # đang kéo thanh tua / kéo cửa sổ → đừng ẩn giữa chừng
            )
            if keep:
                self._away_since = None
            elif self._away_since is None:
                self._away_since = now
            elif now - self._away_since >= self.LEAVE_HIDE_DELAY:
                self._hide()
            # Đồng hồ tự ép topmost định kỳ (ensure_window_visible) → giữ popup luôn nằm trên
            if self.shown and now - self._last_raise >= 1.0:
                self._last_raise = now
                raise_topmost_noactivate(self.win)
                self._set_clock_hidden(True)  # phòng chỗ khác lỡ khôi phục alpha đồng hồ
        else:
            can_show = (
                self.cfg.get("hover_enabled", True)
                and not self.app.config.get("click_through", False)  # xuyên chuột: popup sẽ chặn click
                and not menu_open
                and not getattr(self.app, "drag_moved", False)
            )
            if can_show and over_clock:
                if self._hover_since is None or is_any_mouse_button_down():
                    # Bắt đầu đếm, hoặc đếm lại từ đầu khi đang bấm chuột vào đồng hồ
                    # (click / double-click / kéo / chuột phải) → thao tác đồng hồ không bị video bật lên
                    self._hover_since = now
                elif now - self._hover_since >= self.get_hover_delay():
                    self._hover_since = None
                    self._show()
            else:
                self._hover_since = None

        self._schedule_tick()

    def _on_player_exited(self):
        """mpv đã thoát (người dùng bấm q, hết lỗi mạng, link hỏng...)."""
        early = (time.time() - self._started_at) < self.EARLY_EXIT_SEC
        err = self.player.last_error_text()
        self.player.stop()
        self._teardown_window()
        if early:
            detail = f"\n\nChi tiết:\n{err}" if err else ""
            self.app._safe_messagebox(
                "showerror",
                "Không phát được video",
                "Video không phát được (link riêng tư / bị chặn vùng / mất mạng, "
                "hoặc yt-dlp đã cũ cần cập nhật) (｡•́︿•̀｡)" + detail,
            )
