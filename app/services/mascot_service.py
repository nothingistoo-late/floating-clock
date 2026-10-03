"""
Pixel Mascot Manager (Virtual Desktop Pet)
"""
import os
import random
import tkinter as tk
from app.config import APP_DIR


class MascotManager:
    """Quản lý thú cưng Pixel Art đồng hành trên đồng hồ nổi"""
    
    MEOW_DIALOGUES = [
        "Meow! Cố lên sen ơi! ( =^･ω･^= )",
        "Meow! Làm việc chăm chỉ rồi lãnh lương nào! ฅ^•ﻌ•^ฅ",
        "Meow! Nhớ uống nước và chớp mắt nha! ( ˶ᵔ ᵕ ᵔ˶ )",
        "Meow! Sắp tan làm rùi đó, đừng nản chí! ( ๑‾̀◡‾́)و",
        "Meow! Focus cao độ không xao nhãng nha sen! ( •̀ ω •́ )✧",
        "Puuuurrr... Chúc sen một ngày ngập tràn niềm vui! ( ˘ ³˘)♥",
    ]

    def __init__(self, root, config):
        self.root = root
        self.config = config
        dir_candidates = [
            os.path.join(APP_DIR, "app", "assets", "mascot"),
            os.path.join(APP_DIR, "assets", "mascot"),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "mascot"),
        ]
        self.mascot_dir = next((d for d in dir_candidates if os.path.exists(d)), dir_candidates[0])
        self.frames = {"idle": [], "work": [], "leaving": []}
        self.intervals = {
            "work": 0.14,      # Gõ phím lách cách liên hoàn cực mượt (chu kỳ 6 frame ~0.84s)
            "leaving": 0.16,   # Nhảy chân sáo hào hứng vui vẻ (chu kỳ 6 frame ~0.96s)
            "idle": 0.28,      # Thở phập phồng & chớp mắt nhịp nhàng (chu kỳ 6 frame ~1.68s)
        }
        self.current_state = "idle"
        self.current_frame_idx = 0
        self.last_frame_time = 0.0
        self._load_sprites()

    def _load_sprites(self):
        """Nạp các file PNG animation 6 frames vào bộ nhớ PhotoImage"""
        state_configs = {
            "idle": [f"cat_idle_{i}.png" for i in range(6)],
            "work": [f"cat_work_{i}.png" for i in range(6)],
            "leaving": [f"cat_leaving_{i}.png" for i in range(6)],
        }
        for state, fnames in state_configs.items():
            self.frames[state] = []
            for fname in fnames:
                fpath = os.path.join(self.mascot_dir, fname)
                if os.path.exists(fpath):
                    try:
                        img = tk.PhotoImage(file=fpath, master=self.root)
                        self.frames[state].append(img)
                    except Exception:
                        pass
            # Nếu chưa có frame con nào thì fallback sang file gốc
            if not self.frames[state]:
                fallback_path = os.path.join(self.mascot_dir, f"cat_{state}.png")
                if os.path.exists(fallback_path):
                    try:
                        self.frames[state].append(tk.PhotoImage(file=fallback_path, master=self.root))
                    except Exception:
                        pass

    def get_state(self, current_mode, pomo_running, is_leaving_soon):
        """Xác định trạng thái của bé mèo dựa trên ngữ cảnh hoạt động"""
        if pomo_running or (current_mode in ("timer", "stopwatch") and pomo_running):
            return "work"
        if is_leaving_soon or current_mode == "target_time":
            return "leaving"
        return "idle"

    def get_animated_sprite(self, state, now_ts):
        """Lấy frame animation hiện tại theo nhịp thời gian (chu kỳ 6 frames)"""
        frames_list = self.frames.get(state) or self.frames.get("idle", [])
        if not frames_list:
            return None

        # Chuyển trạng thái tức thì khi đổi ngữ cảnh hoặc được click
        if getattr(self, "current_state", None) != state:
            self.current_state = state
            self.current_frame_idx = 0
            self.last_frame_time = now_ts
            return frames_list[0]

        # Đổi frame khi đến nhịp interval của trạng thái đó
        interval = self.intervals.get(state, 0.2)
        if now_ts - self.last_frame_time >= interval:
            self.current_frame_idx = (self.current_frame_idx + 1) % len(frames_list)
            self.last_frame_time = now_ts

        idx = self.current_frame_idx % len(frames_list)
        return frames_list[idx]

    def get_random_meow(self):
        """Lấy câu thoại tương tác ngẫu nhiên khi click vào bé mèo"""
        return random.choice(self.MEOW_DIALOGUES)
