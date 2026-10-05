"""
Pixel Mascot Manager (Virtual Desktop Pet)
"""
import os
import random
import tkinter as tk
from datetime import datetime
from app.config import APP_DIR, BUNDLE_DIR


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
            os.path.join(BUNDLE_DIR, "app", "assets", "mascot"),
            os.path.join(APP_DIR, "app", "assets", "mascot"),
            os.path.join(APP_DIR, "assets", "mascot"),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "mascot"),
        ]
        self.mascot_dir = next((d for d in dir_candidates if os.path.exists(d)), dir_candidates[0])
        self.frames = {"idle": [], "work": [], "leaving": [], "sleep": []}
        self.intervals = {
            "idle": 0.40,      # Thở & chớp mắt nhịp nhàng (chu kỳ 6 frame ~2.4s)
            "work": 0.40,      # Gõ phím chậm rãi, thư thả (chu kỳ 12 frame ~4.8s)
            "leaving": 0.35,   # Nhảy chân sáo & ăn mừng bay bổng (chu kỳ 6 frame ~2.1s)
            "sleep": 0.45,     # Ngủ say sưa, thở phập phồng êm đềm (chu kỳ 12 frame ~5.4s)
        }
        self.current_state = "idle"
        self.current_frame_idx = 0
        self.last_frame_time = 0.0
        self._load_sprites()

    def _load_sprites(self):
        """Nạp các file PNG animation vào bộ nhớ PhotoImage (tự động nhận diện số frame)"""
        for state in ["idle", "work", "leaving", "sleep"]:
            self.frames[state] = []
            i = 0
            while True:
                fpath = os.path.join(self.mascot_dir, f"cat_{state}_{i}.png")
                if os.path.exists(fpath):
                    try:
                        img = tk.PhotoImage(file=fpath, master=self.root)
                        self.frames[state].append(img)
                        i += 1
                    except Exception:
                        break
                else:
                    break
            # Nếu chưa có frame con nào thì fallback sang file gốc
            if not self.frames[state]:
                fallback_path = os.path.join(self.mascot_dir, f"cat_{state}.png")
                if os.path.exists(fallback_path):
                    try:
                        self.frames[state].append(tk.PhotoImage(file=fallback_path, master=self.root))
                    except Exception:
                        pass

    def get_state(self, current_mode, pomo_running, pomo_stage="work", is_leaving_soon=False, now=None):
        """
        Xác định trạng thái của bé mèo dựa trên ngữ cảnh hoạt động và thời gian biểu:
        - Giờ ngủ trưa & Đêm muộn (sau 22:00 -> sáng hôm sau): 'sleep' (cuộn tròn ngủ khò khò).
        - Pomodoro: 'work' khi đang cày cuốc, 'idle'/'sleep' khi nghỉ giải lao.
        - Giờ làm việc: 'work' (08:30 -> tan làm, trừ giờ nghỉ trưa & 30p sắp về).
        - Sắp về (30p trước tan làm) hoặc Ngoài giờ làm việc ban ngày (sau tan làm -> trước 22:00): 'leaving'.
        """
        if now is None:
            now = datetime.now()

        # 1. Kiểm tra giờ ngủ trưa & Đêm muộn (Ưu tiên trạng thái Sleep)
        work_cfg = self.config.get("work_departure", {})
        start_str = work_cfg.get("start_time", "08:30")
        dep_str = work_cfg.get("sat_time", "16:00") if now.weekday() == 5 else work_cfg.get("mon_fri_time", "17:45")
        lunch_start_str = work_cfg.get("lunch_start", "12:00")
        lunch_end_str = work_cfg.get("lunch_end", "13:30")

        today_str = now.strftime("%Y-%m-%d")
        try:
            dt_start = datetime.strptime(f"{today_str} {start_str}:00", "%Y-%m-%d %H:%M:%S")
            dt_dep = datetime.strptime(f"{today_str} {dep_str}:00", "%Y-%m-%d %H:%M:%S")
            dt_lunch_start = datetime.strptime(f"{today_str} {lunch_start_str}:00", "%Y-%m-%d %H:%M:%S")
            dt_lunch_end = datetime.strptime(f"{today_str} {lunch_end_str}:00", "%Y-%m-%d %H:%M:%S")
        except Exception:
            dt_start = now.replace(hour=8, minute=30, second=0)
            dt_dep = now.replace(hour=17, minute=45, second=0)
            dt_lunch_start = now.replace(hour=12, minute=0, second=0)
            dt_lunch_end = now.replace(hour=13, minute=30, second=0)

        # 2. Ưu tiên chế độ Pomodoro khi người dùng chủ động kích hoạt
        if pomo_running:
            if pomo_stage in ("break", "long_break"):
                if dt_lunch_start <= now < dt_lunch_end or now.hour >= 22 or now < dt_start:
                    return "sleep"
                return "idle"
            return "work"

        # 3. Nếu đang chạy Timer hoặc Stopwatch
        if current_mode in ("timer", "stopwatch") and pomo_running:
            return "work"

        # 4. Giờ ngủ ban đêm (Từ 22:00 tối đến trước giờ bắt đầu làm việc sáng hôm sau)
        if now.hour >= 22 or now < dt_start:
            return "sleep"

        # 5. Giờ ngủ trưa (Từ lunch_start đến lunch_end)
        if dt_lunch_start <= now < dt_lunch_end:
            return "sleep"

        # 6. Ngày nghỉ cuối tuần (Chủ Nhật) -> Ngoài giờ làm việc, nhảy nhót vui tươi
        if now.weekday() == 6:
            return "leaving"

        # 7. Sắp tan làm (trong vòng 30 phút trước giờ về)
        diff_to_dep_min = (dt_dep - now).total_seconds() / 60.0
        if 0 <= diff_to_dep_min <= 30 or is_leaving_soon:
            return "leaving"

        # 8. Sau giờ tan làm (đến trước 22:00 đêm) -> Nhảy nhót ăn mừng
        if now >= dt_dep:
            return "leaving"

        # 9. Trong giờ làm việc chính thức -> Cày cuốc gõ phím
        return "work"

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
