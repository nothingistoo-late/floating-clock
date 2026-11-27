"""
Thanh điều khiển video kiểu YouTube (luôn hiện dưới khung video):

  ⏮ ⏯ ⏭   1:23 / 3:45   ━━━━━━●──────────   🔊 ━━●──   1x   ⚙   ◢

- Thanh tua & thanh âm lượng: bấm hoặc kéo.
- 1x: chọn tốc độ. ⚙: chất lượng, tốc độ, lặp lại, kích thước, độ mờ.
- ◢: kéo để đổi cỡ khung video.
Chỉ lo phần giao diện; mọi hành động gọi ngược về YouTubeOverlay.
"""
import tkinter as tk

BG = "#11141c"
FG = "#E2E8F0"
FG_DIM = "#475569"
ACCENT = "#EF4444"
TROUGH = "#334155"


def format_time(seconds):
    """83 → '1:23', 3725 → '1:02:05'."""
    try:
        s = max(0, int(seconds))
    except Exception:
        return "0:00"
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


class BarSlider(tk.Canvas):
    """Thanh trượt mảnh vẽ bằng Canvas (đẹp hơn tk.Scale): bấm / kéo để chọn tỉ lệ 0..1."""

    def __init__(self, master, on_change=None, on_release=None, width=80, height=14, color=ACCENT, **kw):
        super().__init__(master, width=width, height=height, bg=BG, highlightthickness=0, bd=0,
                         cursor="hand2", **kw)
        self.on_change = on_change
        self.on_release = on_release
        self.color = color
        self.fraction = 0.0
        self.dragging = False
        self.bind("<Configure>", lambda e: self._redraw())
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_motion)
        self.bind("<ButtonRelease-1>", self._on_release)

    def set_fraction(self, f):
        """Cập nhật từ trạng thái player (bỏ qua khi người dùng đang kéo)."""
        if self.dragging:
            return
        f = max(0.0, min(1.0, float(f or 0.0)))
        if abs(f - self.fraction) >= 0.002:
            self.fraction = f
            self._redraw()

    def _fraction_at(self, x):
        w = max(1, self.winfo_width() - 8)
        return max(0.0, min(1.0, (x - 4) / w))

    def _on_press(self, event):
        self.dragging = True
        self._on_motion(event)
        return "break"

    def _on_motion(self, event):
        self.fraction = self._fraction_at(event.x)
        self._redraw()
        if self.on_change:
            self.on_change(self.fraction)
        return "break"

    def _on_release(self, event):
        self.fraction = self._fraction_at(event.x)
        self.dragging = False
        self._redraw()
        if self.on_release:
            self.on_release(self.fraction)
        return "break"

    def _redraw(self):
        self.delete("all")
        w = max(10, self.winfo_width())
        h = max(6, self.winfo_height())
        cy = h // 2
        x0, x1 = 4, w - 4
        xf = x0 + (x1 - x0) * self.fraction
        self.create_line(x0, cy, x1, cy, fill=TROUGH, width=3, capstyle="round")
        if xf > x0:
            self.create_line(x0, cy, xf, cy, fill=self.color, width=3, capstyle="round")
        r = 5 if self.dragging else 4
        self.create_oval(xf - r, cy - r, xf + r, cy + r, fill=self.color, outline="")


class YouTubeControlBar(tk.Frame):
    """Thanh điều khiển dưới video. `overlay` là YouTubeOverlay (cung cấp hành động & menu)."""

    HEIGHT = 30

    def __init__(self, master, overlay):
        super().__init__(master, bg=BG, height=self.HEIGHT)
        self.pack_propagate(False)
        self.overlay = overlay
        self._seek_preview = None   # giây đang kéo tới (hiện ở ô thời gian khi kéo thanh tua)

        btn = dict(font=("Segoe UI Symbol", 10), bg=BG, fg=FG, activebackground="#334155",
                   activeforeground="#FFFFFF", relief="flat", bd=0, padx=5, pady=0, cursor="hand2")

        self.btn_prev = tk.Button(self, text="⏮", command=overlay.prev_video, **btn)
        self.btn_play = tk.Button(self, text="⏸", width=2, command=overlay.toggle_pause, **btn)
        self.btn_next = tk.Button(self, text="⏭", command=overlay.next_video, **btn)
        for b in (self.btn_prev, self.btn_play, self.btn_next):
            b.pack(side="left")

        self.lbl_time = tk.Label(self, text="0:00 / 0:00", font=("Consolas", 8), bg=BG, fg="#94A3B8")
        self.lbl_time.pack(side="left", padx=(4, 6))

        # Bên phải (pack trước để thanh tua chiếm phần còn lại ở giữa)
        self.grip = tk.Label(self, text="◢", font=("Segoe UI", 10), bg=BG, fg="#94A3B8",
                             cursor="size_nw_se", padx=3)
        self.grip.pack(side="right")
        self.btn_settings = tk.Button(self, text="⚙", command=self._open_settings, **btn)
        self.btn_settings.pack(side="right")
        self.btn_speed = tk.Button(self, text="1x", command=self._open_speed,
                                   **{**btn, "font": ("Segoe UI", 8, "bold")})
        self.btn_speed.pack(side="right")
        self.vol = BarSlider(self, on_change=overlay.on_volume_drag, on_release=overlay.on_volume_release,
                             width=60, color="#E2E8F0")
        self.vol.pack(side="right", padx=(0, 4))
        self.btn_mute = tk.Button(self, text="🔊", command=overlay.toggle_mute,
                                  **{**btn, "font": ("Segoe UI Emoji", 9)})
        self.btn_mute.pack(side="right")

        self.seek = BarSlider(self, on_change=self._on_seek_drag, on_release=self._on_seek_release, width=60)
        self.seek.pack(side="left", fill="x", expand=True, padx=(0, 6))

        # Lăn chuột trên thanh âm lượng / nút loa = chỉnh âm lượng
        for w in (self.vol, self.btn_mute):
            w.bind("<MouseWheel>", lambda e: overlay.nudge_volume(5 if e.delta > 0 else -5))

    # ---------------- Cập nhật từ trạng thái player ----------------
    def refresh(self, status, is_playlist):
        st = status or {}
        pos = st.get("time_pos")
        dur = st.get("duration")
        has_pos = isinstance(pos, (int, float))
        has_dur = isinstance(dur, (int, float)) and dur > 0

        # Đã xem hết → nút phát thành "xem lại"
        if st.get("eof"):
            play_txt = "↺"
        else:
            play_txt = "▶" if st.get("paused") else "⏸"
        self._set_text(self.btn_play, play_txt)

        state = "normal" if is_playlist else "disabled"
        for b in (self.btn_prev, self.btn_next):
            if str(b.cget("state")) != state:
                b.configure(state=state, disabledforeground=FG_DIM)

        if self._seek_preview is not None and has_dur:
            shown_pos = self._seek_preview
        else:
            shown_pos = pos if has_pos else 0
        time_txt = f"{format_time(shown_pos)} / {format_time(dur) if has_dur else '--:--'}"
        self._set_text(self.lbl_time, time_txt)
        if has_dur and has_pos:
            self.seek.set_fraction(pos / dur)
        elif not has_dur:
            self.seek.set_fraction(0)

        vol = st.get("volume")
        if isinstance(vol, (int, float)):
            self.vol.set_fraction(vol / 100.0)
        muted = st.get("mute") or (isinstance(vol, (int, float)) and vol <= 0)
        self._set_text(self.btn_mute, "🔇" if muted else "🔊")

        spd = st.get("speed")
        if isinstance(spd, (int, float)):
            self._set_text(self.btn_speed, f"{spd:g}x")

    @staticmethod
    def _set_text(widget, txt):
        if widget.cget("text") != txt:
            widget.configure(text=txt)

    # ---------------- Tua ----------------
    def _on_seek_drag(self, fraction):
        dur = (self.overlay.player.status or {}).get("duration")
        if isinstance(dur, (int, float)) and dur > 0:
            self._seek_preview = fraction * dur
            self.lbl_time.configure(text=f"{format_time(self._seek_preview)} / {format_time(dur)}")

    def _on_seek_release(self, fraction):
        self._seek_preview = None
        self.overlay.seek_fraction(fraction)

    # ---------------- Menu ----------------
    def _open_speed(self):
        self.overlay.open_speed_menu(self.btn_speed)

    def _open_settings(self):
        self.overlay.open_settings_menu(self.btn_settings)
