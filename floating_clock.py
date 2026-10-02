"""
====================================================================
🕒 TOP FLOATING CLOCK & MULTI-TOOL (ĐỒNG HỒ NỔI ĐA NĂNG ĐỈNH MÀN HÌNH)
====================================================================
Các chức năng chính:
 1. 🕒 Đồng hồ thời gian thực (Clock): Chuẩn xác, tùy chọn 12h/24h, mili-giây, ngày tháng.
 2. ⏳ Đếm ngược (Countdown Timer): Đặt phút/giây tùy ý, presets nhanh, chuông báo khi hết giờ.
 3. 🎯 Đến thời gian & Tan làm (Work Departure Schedule):
    - Tự động nhận diện: Thứ 2 - Thứ 6: 17h45 | Thứ 7: 16h00 | Tùy chỉnh linh hoạt.
 4. 🤖 AI Động Viên GenZ & Motivational Quotes:
    - Hỗ trợ gắn API Key (Google Gemini, OpenAI, Groq, OpenRouter) để AI tự tạo câu GenZ hài hước theo ngữ cảnh.
    - Bộ sưu tập 50+ câu GenZ đỉnh nóc kịch trần tích hợp sẵn khi không có mạng/key.
 5. 💧 Nhắc nhở uống nước & Vươn vai (Hydration & Posture Reminder):
    - Tự động nhắc sau mỗi 30p/45p/60p giúp bảo vệ sức khỏe khi ngồi máy tính.
 6. 📊 % Tiến độ ngày làm việc (Workday Progress Bar):
    - Đo lường trực quan % hoàn thành ngày làm việc theo thời gian thực.
 7. ⏰ Báo thức thông minh (Multi Alarm): Đặt nhiều mốc báo thức, ghi chú, chuông réo rắt, Snooze/Dismiss.
 8. ⏱️ Bấm giờ thể thao (Stopwatch): Đo thời gian chính xác từng 1/100s, ghi vòng (Lap).
 9. 🍅 Pomodoro Timer: 25m Focus / 5m Break hỗ trợ làm việc hiệu quả.
 10. 🎨 Tùy biến cao cấp: Luôn ghim trên cùng (Always-on-top), Xuyên chuột (F8), Linh vật (Mascot), Đổi màu Neon.
====================================================================
"""

import json
import os
import sys

# Prevent crashes in pythonw / noconsole when stdout/stderr are None
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

import time
import math
import random
import ctypes
import threading
import urllib.request
import urllib.error
import ssl
import wave
import struct
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk, messagebox, colorchooser
import winsound

if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(APP_DIR, "clock_config.json")
# Win32 API Constants for Click-through
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020

import winreg

# Win32 Memory & CPU structures
class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]

def get_ram_usage_percent():
    try:
        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
            return stat.dwMemoryLoad
    except Exception:
        pass
    return 0

_prev_idle = 0
_prev_kernel = 0
_prev_user = 0

def get_cpu_usage_percent():
    global _prev_idle, _prev_kernel, _prev_user
    try:
        idle = ctypes.c_ulonglong()
        kernel = ctypes.c_ulonglong()
        user = ctypes.c_ulonglong()
        if ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)):
            i = idle.value
            k = kernel.value
            u = user.value
            if _prev_kernel == 0:
                _prev_idle, _prev_kernel, _prev_user = i, k, u
                return 0
            d_idle = i - _prev_idle
            d_kernel = k - _prev_kernel
            d_user = u - _prev_user
            _prev_idle, _prev_kernel, _prev_user = i, k, u
            total = d_kernel + d_user
            if total > 0:
                pct = int((1.0 - (d_idle / total)) * 100)
                return max(0, min(100, pct))
    except Exception:
        pass
    return 0

def set_start_with_windows(enable=True):
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    app_name = "FloatingClock"
    exe_path = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__)
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        if enable:
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, f'"{exe_path}"')
        else:
            try:
                winreg.DeleteValue(key, app_name)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except Exception:
        return False

def is_start_with_windows():
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    app_name = "FloatingClock"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
        val, _ = winreg.QueryValueEx(key, app_name)
        winreg.CloseKey(key)
        return bool(val)
    except Exception:
        return False

def set_click_through(hwnd, enable=True):
    try:
        user32 = ctypes.windll.user32
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        if enable:
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED | WS_EX_TRANSPARENT)
        else:
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, (style | WS_EX_LAYERED) & ~WS_EX_TRANSPARENT)
    except Exception:
        pass


# ==========================================
# 🔊 SOUND MANAGER (Trình phát âm thanh chuông)
# ==========================================
class SoundManager:
    def __init__(self):
        self._ringing = False
        self._thread = None
        self.sound_enabled = True

    def is_ringing(self):
        return self._ringing

    def stop_alarm(self):
        self._ringing = False

    def play_alarm_loop(self, message="Báo thức"):
        if not self.sound_enabled:
            return
        self.stop_alarm()
        self._ringing = True

        def _worker():
            melody = [
                (1046, 120), (1318, 120), (1568, 120), (2093, 220),
                (1568, 120), (2093, 300), (0, 150),
                (1046, 120), (1318, 120), (1568, 120), (2093, 220),
                (2349, 150), (2093, 400), (0, 300)
            ]
            while self._ringing:
                for freq, dur in melody:
                    if not self._ringing:
                        break
                    if freq == 0:
                        time.sleep(dur / 1000.0)
                    else:
                        try:
                            winsound.Beep(freq, dur)
                        except Exception:
                            pass
                time.sleep(0.2)

        self._thread = threading.Thread(target=_worker, daemon=True)
        self._thread.start()

    def play_timer_chime(self):
        if not self.sound_enabled:
            return
        def _worker():
            notes = [(880, 150), (1175, 150), (1318, 150), (1760, 350)]
            for f, d in notes:
                try:
                    winsound.Beep(f, d)
                except Exception:
                    pass
        threading.Thread(target=_worker, daemon=True).start()

    def play_water_chime(self):
        if not self.sound_enabled:
            return
        def _worker():
            notes = [(1318, 180), (1760, 300)]
            for f, d in notes:
                try:
                    winsound.Beep(f, d)
                except Exception:
                    pass
        threading.Thread(target=_worker, daemon=True).start()

    def play_pomo_break(self):
        if not self.sound_enabled:
            return
        def _worker():
            notes = [(1046, 150), (1318, 150), (1568, 250), (1318, 150), (1568, 350)]
            for f, d in notes:
                try:
                    winsound.Beep(f, d)
                except Exception:
                    pass
        threading.Thread(target=_worker, daemon=True).start()

    def play_tick(self):
        if not self.sound_enabled:
            return
        def _worker():
            try:
                winsound.Beep(1200, 40)
            except Exception:
                pass
        threading.Thread(target=_worker, daemon=True).start()


sound_mgr = SoundManager()


# ==========================================
# 🌦️ WEATHER MANAGER (Dự Báo Thời Tiết Realtime)
# ==========================================
CITY_COORDINATES = {
    "Hà Nội": (21.0285, 105.8542),
    "TP. Hồ Chí Minh": (10.8231, 106.6297),
    "Đà Nẵng": (16.0544, 108.2022),
    "Hải Phòng": (20.8449, 106.6881),
    "Cần Thơ": (10.0452, 105.7469),
    "Nha Trang": (12.2388, 109.1967),
    "Đà Lạt": (11.9404, 108.4583),
    "Huế": (16.4637, 107.5909),
    "Vũng Tàu": (10.3460, 107.0843),
    "Quy Nhơn": (13.7830, 109.2197),
}

WEATHER_CODE_MAP = {
    0: ("☀️", "Nắng ráo"),
    1: ("🌤️", "Nắng nhẹ / Ít mây"),
    2: ("⛅", "Có mây"),
    3: ("☁️", "Nhiều mây"),
    45: ("🌫️", "Sương mù"),
    48: ("🌫️", "Sương mù lạnh"),
    51: ("🌦️", "Mưa phùn nhẹ"),
    53: ("🌦️", "Mưa phùn vừa"),
    55: ("🌧️", "Mưa phùn dày"),
    61: ("🌧️", "Mưa nhỏ"),
    63: ("🌧️", "Mưa vừa"),
    65: ("🌧️", "Mưa to"),
    71: ("❄️", "Tuyết rơi nhẹ"),
    73: ("❄️", "Tuyết rơi vừa"),
    75: ("❄️", "Tuyết rơi dày"),
    80: ("🌦️", "Mưa rào nhẹ"),
    81: ("🌦️", "Mưa rào vừa"),
    82: ("⛈️", "Mưa rào rất to"),
    95: ("⛈️", "Giông bão"),
    96: ("⛈️", "Giông bão kèm mưa đá"),
    99: ("⛈️", "Giông bão dữ dội"),
}

class WeatherManager:
    def __init__(self, config):
        self.config = config
        self.last_fetch_time = 0
        self.current_weather_str = ""
        self.current_data = {}
        self.is_fetching = False

    def fetch_weather(self, callback=None):
        w_cfg = self.config.get("weather", {})
        if not w_cfg.get("enabled", True):
            return

        city = w_cfg.get("city_name", "Hà Nội")
        lat, lon = CITY_COORDINATES.get(city, (w_cfg.get("lat", 21.0285), w_cfg.get("lon", 105.8542)))

        def _worker():
            self.is_fetching = True
            try:
                ctx = ssl._create_unverified_context()
                url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
                req = urllib.request.Request(url, headers={"User-Agent": "TopFloatingClock/2.0"})
                with urllib.request.urlopen(req, timeout=6, context=ctx) as res:
                    data = json.loads(res.read().decode("utf-8"))
                    cw = data.get("current_weather", {})
                    temp = cw.get("temperature", 28.0)
                    w_code = cw.get("weathercode", 0)
                    wind = cw.get("windspeed", 0.0)

                    icon, desc = WEATHER_CODE_MAP.get(w_code, ("🌤️", "Thời tiết tốt"))
                    txt = f"{icon} {city}: {temp:.0f}°C • {desc}"

                    self.current_weather_str = txt
                    self.current_data = {
                        "city": city,
                        "temp": temp,
                        "wind": wind,
                        "icon": icon,
                        "desc": desc,
                        "time": cw.get("time", "")
                    }
                    self.last_fetch_time = time.time()
                    if callback:
                        callback(txt, self.current_data)
            except Exception:
                pass
            finally:
                self.is_fetching = False

        threading.Thread(target=_worker, daemon=True).start()


# ==========================================
# 🎧 FOCUS SOUND MANAGER (Âm Thanh Tập Trung / White Noise)
# ==========================================
class FocusSoundManager:
    SOUND_TYPES = {
        "rain": {"name": "Mưa rào êm dịu (Rainfall)", "icon": "🌧️"},
        "ocean": {"name": "Sóng biển dạt dào (Ocean Waves)", "icon": "🌊"},
        "brown_noise": {"name": "Tiếng ồn nâu sâu lắng (Brown Noise)", "icon": "🧘"},
        "white_noise": {"name": "Tiếng ồn trắng tĩnh tâm (White Noise)", "icon": "📻"},
        "alpha_wave": {"name": "Sóng não Alpha 432Hz (Deep Focus)", "icon": "🧠"},
        "cafe": {"name": "Quán cà phê chill (Cafe Ambient)", "icon": "☕"},
    }

    def __init__(self, config):
        self.config = config
        self.is_playing = False
        self.current_sound_type = config.get("focus_sound", {}).get("sound_type", "rain")
        self.temp_sound_file = os.path.join(APP_DIR, "_ambient_loop.wav")

    @property
    def current_sound(self):
        return self.current_sound_type

    @current_sound.setter
    def current_sound(self, val):
        self.current_sound_type = val

    def generate_sound_wav(self, sound_type="rain", duration_sec=6, sample_rate=22050):
        num_samples = int(duration_sec * sample_rate)
        try:
            with wave.open(self.temp_sound_file, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)

                raw_data = bytearray()
                last_val = 0.0

                if sound_type == "rain":
                    for i in range(num_samples):
                        white = random.uniform(-1.0, 1.0)
                        last_val = (last_val * 0.94) + (white * 0.06)
                        if random.random() < 0.003:
                            val = last_val * 0.7 + random.uniform(-0.6, 0.6) * 0.3
                        else:
                            val = last_val
                        val_c = max(-1.0, min(1.0, val * 1.2))
                        raw_data.extend(struct.pack('<h', int(val_c * 32767)))

                elif sound_type == "ocean":
                    wave_period = 5.0
                    for i in range(num_samples):
                        t = i / sample_rate
                        surge = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(2 * math.pi * t / wave_period))
                        white = random.uniform(-1.0, 1.0)
                        last_val = (last_val * 0.92) + (white * 0.08)
                        val_c = max(-1.0, min(1.0, last_val * surge * 1.5))
                        raw_data.extend(struct.pack('<h', int(val_c * 32767)))

                elif sound_type == "brown_noise":
                    for i in range(num_samples):
                        white = random.uniform(-1.0, 1.0)
                        last_val = (last_val * 0.985) + (white * 0.015)
                        val_c = max(-1.0, min(1.0, last_val * 2.5))
                        raw_data.extend(struct.pack('<h', int(val_c * 32767)))

                elif sound_type == "white_noise":
                    for i in range(num_samples):
                        val = random.uniform(-0.25, 0.25)
                        raw_data.extend(struct.pack('<h', int(val * 32767)))

                elif sound_type == "alpha_wave":
                    for i in range(num_samples):
                        t = i / sample_rate
                        carrier = math.sin(2 * math.pi * 432.0 * t)
                        mod = 0.75 + 0.25 * math.sin(2 * math.pi * 10.0 * t)
                        val_c = carrier * mod * 0.2
                        raw_data.extend(struct.pack('<h', int(val_c * 32767)))

                elif sound_type == "cafe":
                    for i in range(num_samples):
                        white = random.uniform(-1.0, 1.0)
                        last_val = (last_val * 0.93) + (white * 0.07)
                        val = last_val * 0.6
                        if random.random() < 0.0006:
                            val += random.uniform(-0.8, 0.8)
                        val_c = max(-1.0, min(1.0, val))
                        raw_data.extend(struct.pack('<h', int(val_c * 32767)))

                wf.writeframes(raw_data)
            return True
        except Exception:
            return False

    def play(self, sound_type=None):
        if sound_type:
            self.current_sound_type = sound_type
        if self.generate_sound_wav(self.current_sound_type):
            try:
                winsound.PlaySound(self.temp_sound_file, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP)
                self.is_playing = True
                return True
            except Exception:
                pass
        return False

    def stop(self):
        try:
            winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception:
            pass
        self.is_playing = False

    def toggle(self, sound_type=None):
        if self.is_playing:
            self.stop()
            return False
        else:
            return self.play(sound_type)


# ==========================================
# 💬 GENZ MOTIVATION & QUOTES POOL (OFFLINE & CLOUD)
# ==========================================
DEFAULT_QUOTES = {
    "morning": [
        "☕ Cà phê sáng làm một ngụm rồi flex trình nào fen!",
        "🚀 Sáng nay slay hết mình, bug nào cũng phải quỳ gối xin tha! 😎",
        "💪 Kiếp làm thuê nhưng tâm hồn làm chủ, gét gô ngày mới! 🔥",
        "☀️ Khởi đầu ngày mới đỉnh nóc kịch trần, làm việc hết nước chấm! ✨",
        "🎯 Bật mode tập trung cao độ, lương ting ting đang vẫy gọi! 💸",
        "✨ Hôm nay bạn đã slay chưa? Mở màn hình lên tỏa sáng nào! 💅",
        "🔥 Năng lượng hôm nay 1000%, sẵn sàng gánh team công ty! 🚀",
        "⚡ Tự nhủ bản thân: Cố kiếm tiền để đi shopping không cần nhìn giá! 🛍️",
        "💎 Một tâm hồn đẹp trong một thân thể tràn đầy caffeine! ☕"
    ],
    "lunch": [
        "🍱 Sắp đến giờ cơm trưa rồi, nạp năng lượng rồi healing tiếp! 🍜",
        "🍜 Bụng đói là não overthinking liền, trưa nay làm bữa ngon nhé! 🍛",
        "🍛 Nghỉ tay đi ăn thôi fen, làm việc là phụ, ăn ngon là chính! 🤤",
        "🥗 Trưa nay làm cốc trà sữa full topping cho đời nó tươi! 🧋",
        "🍔 Nạp đạm nạp calo để chiều nay gánh team công ty nào! 🍟",
        "🍲 Ăn no căng bụng rồi chợp mắt 15 phút là đỉnh chóp! 😴",
        "🍗 Đừng nhịn ăn trưa nha fen, có thực mới vực được deadline! 🍕"
    ],
    "afternoon": [
        "💦 Rửa mặt một phát, làm cốc nước rồi tiếp tục cày cuốc nào! 💦",
        "🔥 Đừng overthinking nữa, cứ slay hết mình đi bro! 🔥",
        "🧠 Ngồi thẳng lưng lên fen, gù lưng là không flex được outfit đâu! 🧍",
        "💎 Deadline dí sát đít nhưng thần thái vẫn 10 điểm không có nhưng! 💯",
        "⚡ Lao động là vinh quang, tan làm đúng giờ là chân lý! 🏃‍♂️💨",
        "🧘 Tâm bất biến giữa dòng đời deadline xô đẩy! 🧘‍♂️",
        "🌟 Không có áp lực thì không có kim cương, fen đỉnh chóp luôn! 💎",
        "🎪 Chạy deadline như chạy show, mệt nhưng mà nó cuốn! 🤡",
        "🔋 Đang nạp lại năng lượng: 5 phút làm việc, 10 phút suy ngẫm nhân sinh! 🧘",
        "✨ Slay girl/boy không bao giờ khuất phục trước task khó! 💅",
        "🚀 Bật nhạc lofi lên rồi tập trung cày nốt nào fen! 🎧",
        "☕ Cần gấp 1 ngụm cà phê để hồi sinh linh hồn buổi chiều! ☕"
    ],
    "leaving_soon": [
        "🏃‍♂️💨 Chỉ còn một chút nữa là tan làm rồi, đếm ngược giải phóng thôi!",
        "🍻 Sắp 17h45 rồi, dọn dẹp task chuẩn bị về quẩy thôi fen! 🎉",
        "🎉 Cố lên người anh em, sắp đến giờ về với tự do và healing rồi! 💆‍♂️",
        "🍺 Chiều nay làm cốc bia tươi hay đi lượn phố chill chill nào? 🍻",
        "🚴‍♂️ Sáng hướng nội, trưa hướng ngoại, chiều hướng về nhà! 🏠",
        "🏖️ Gom đồ vào balo, đếm từng giây chuẩn bị phóng như một cơn gió! 💨",
        "🍕 Tối nay ăn gì ngon để tự thưởng cho sự chăm chỉ hôm nay nhỉ? 🍔"
    ],
    "friday": [
        "🎉 Hôm nay THỨ 6 rồi! Chiều nay tan làm là quẩy tưng bừng cuối tuần!",
        "🏖️ Thứ 6 máu hơn thứ 2, tràn đầy hứng khởi về đích tuần này thôi! 🔥",
        "🍻 Thứ 6 vui vẻ! Chuẩn bị tinh thần xõa hết nấc thôi fen! 🏄‍♂️",
        "✨ Thứ 6 thần thánh: Deadline để tuần sau, tối nay là phải đi chill! 🍸"
    ],
    "saturday": [
        "🏖️ Hôm nay THỨ 7 về sớm lúc 16h! Cuối tuần rực rỡ đang chờ đón!",
        "🏄‍♂️ Làm nốt buổi thứ 7 là được xõa hết mình rồi fen ơi! 🏖️",
        "☀️ Thứ 7 tan làm 16h: Về sớm đi dạo phố ngắm hoàng hôn thôi! 🌅"
    ],
    "night": [
        "🎮 Đã hết giờ làm, tắt máy đi chill thôi fen!",
        "❤️ Giữ gìn sức khỏe nha fen, bạn đã vất vả cả ngày hôm nay rồi!",
        "🌙 Tối nay ngủ ngon giấc để mai nạp đầy năng lượng mới nhé! 🛌",
        "🛌 Đắp chăn ấm, lướt tóp tóp xíu rồi ngủ sớm nha fen! 😴"
    ]
}


# ==========================================
# 🤖 AI QUOTE GENERATOR (GEMINI / OPENAI / GROQ)
# ==========================================
class AIManager:
    def __init__(self, config):
        self.config = config
        self.is_fetching = False

    def fetch_ai_quote(self, context_tag, callback=None):
        """Gọi API AI trong background thread để tạo câu động viên GenZ theo ngữ cảnh"""
        ai_cfg = self.config.get("ai_quotes", {})
        api_key = ai_cfg.get("api_key", "").strip()
        provider = ai_cfg.get("provider", "gemini")

        if not api_key:
            quote = self.get_offline_quote(context_tag)
            if callback:
                callback(quote, is_ai=False, error=None)
            return

        if self.is_fetching:
            return
        self.is_fetching = True

        def _worker():
            quote = None
            err = None
            try:
                if provider == "gemini":
                    quote = self._call_gemini(api_key, context_tag)
                elif provider in ("openai", "groq", "openrouter", "custom"):
                    quote = self._call_openai_compatible(ai_cfg, context_tag)
                else:
                    quote = self._call_gemini(api_key, context_tag)
            except Exception as e:
                err = str(e)
                quote = self.get_offline_quote(context_tag)
            finally:
                self.is_fetching = False
                if callback:
                    callback(quote, is_ai=(err is None and quote is not None), error=err)

        threading.Thread(target=_worker, daemon=True).start()

    def _call_gemini(self, api_key, context_tag):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json", "User-Agent": "FloatingClock/1.0"}
        prompt = (
            "Hãy tạo DUY NHẤT 1 câu động viên làm việc ngắn gọn (dưới 15 từ), cực kỳ hài hước, mang đậm phong cách GenZ Việt Nam "
            "(sử dụng linh hoạt từ ngữ trend như: slay, flex, healing, đỉnh nóc kịch trần, ting ting, chill, overthinking, hết nước chấm, bro, fen, gét gô...) "
            f"phù hợp với ngữ cảnh: {context_tag}. Chỉ trả về duy nhất nội dung câu nói kèm icon biểu cảm (emoji), không thêm giải thích hay dấu ngoặc kép."
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.95,
                "maxOutputTokens": 60
            }
        }
        try:
            ctx = urllib.request.ssl._create_unverified_context()
        except Exception:
            ctx = None

        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, context=ctx, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            return text.strip('"\' \n\r')

    def _call_openai_compatible(self, ai_cfg, context_tag):
        api_key = ai_cfg.get("api_key", "").strip()
        provider = ai_cfg.get("provider", "openai")

        if provider == "groq":
            base_url = "https://api.groq.com/openai/v1"
            model = ai_cfg.get("model") or "llama-3.3-70b-versatile"
        else:
            base_url = ai_cfg.get("base_url", "https://api.openai.com/v1").rstrip("/")
            model = ai_cfg.get("model", "gpt-4o-mini").strip() or "gpt-4o-mini"

        url = f"{base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "FloatingClock/1.0"
        }
        prompt = (
            "Hãy tạo DUY NHẤT 1 câu động viên làm việc ngắn gọn (dưới 15 từ), cực kỳ hài hước, mang đậm phong cách GenZ Việt Nam "
            "(sử dụng linh hoạt từ ngữ trend như: slay, flex, healing, đỉnh nóc kịch trần, ting ting, chill, overthinking, hết nước chấm, bro, fen, gét gô...) "
            f"phù hợp với ngữ cảnh: {context_tag}. Chỉ trả về duy nhất nội dung câu nói kèm icon biểu cảm (emoji), không thêm giải thích hay dấu ngoặc kép."
        )
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.95,
            "max_tokens": 60
        }
        try:
            ctx = urllib.request.ssl._create_unverified_context()
        except Exception:
            ctx = None

        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, context=ctx, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            text = data["choices"][0]["message"]["content"].strip()
            return text.strip('"\' \n\r')

    def get_offline_quote(self, context_tag):
        if context_tag in DEFAULT_QUOTES and DEFAULT_QUOTES[context_tag]:
            return random.choice(DEFAULT_QUOTES[context_tag])
        all_q = []
        for v in DEFAULT_QUOTES.values():
            all_q.extend(v)
        return random.choice(all_q) if all_q else "🚀 Cố lên fen ơi, slay hết mình nào!"


# ==========================================
# ⚙️ DEFAULT CONFIGURATION
# ==========================================
DEFAULT_CONFIG = {
    "x": None,
    "y": 10,
    "opacity": 0.90,
    "font_size": 20,
    "text_color": "#00FFCC",
    "bg_color": "#0f131a",
    "border_color": "#2a3447",
    "locked": False,
    "click_through": False,
    "mini_mode": False,              # Chế độ thu nhỏ tối giản (chỉ hiện mỗi số giờ)
    "dynamic_time_color": True,      # Tự động đổi màu theo thời gian (8h Đỏ • 5h Cam • 2h Vàng • 1h Xanh • <1h Trắng)
    "mode": "clock",                 # "clock", "target_time", "timer", "stopwatch", "pomodoro"
    "mascot": "🚀",                  # "🚀", "☕", "🐱", "💎", "🔋", "🎯", "🔥", "None"
    "show_seconds": True,
    "show_ms": False,
    "show_date": True,
    "show_sublabel": True,
    "show_quote": True,
    "show_progress": True,
    "sound_enabled": True,
    "time_format_12h": False,
    # Work Departure Schedule
    "target_time_str": "17:45:00",
    "target_time_label": "Tan làm",
    "target_time_active": True,
    "work_departure": {
        "start_time": "08:30",
        "mon_fri_time": "17:45",
        "sat_time": "16:00",
        "lunch_start": "12:00",
        "lunch_end": "13:15",
        "auto_schedule": True
    },
    # AI Quotes API Configuration
    "ai_quotes": {
        "enabled": True,
        "provider": "gemini",    # "gemini", "openai", "groq", "custom"
        "api_key": "",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "auto_refresh_min": 15
    },
    # Hydration & Posture reminder
    "water_reminder": {
        "enabled": True,
        "interval_min": 45
    },
    # Timer settings
    "timer_duration": 300,
    "timer_remaining": 300,
    "timer_state": "stopped",
    # Alarms list
    "alarms": [
        {"id": 1, "time": "07:00", "label": "Thức dậy / Buổi sáng", "enabled": False, "repeat": True},
        {"id": 2, "time": "12:00", "label": "Giờ ăn trưa & nghỉ ngơi", "enabled": False, "repeat": True},
        {"id": 3, "time": "17:45", "label": "Hết giờ làm việc / Tan ca", "enabled": False, "repeat": True}
    ],
    # Pomodoro settings
    "pomo_work_min": 25,
    "pomo_break_min": 5,
    "pomo_long_break_min": 15,
    "pomo_cycles": 4,
    # Realtime Salary Ticker (Bộ đếm tiền lương theo giây: Ngày & Tháng)
    "salary": {
        "enabled": False,
        "show_daily": True,
        "show_monthly": True,
        "monthly": 15000000,
        "work_days": 22,
        "work_hours": 8.0,
        "calc_cycle": "calendar_month",  # "calendar_month" hoặc "payday_cycle"
        "hidden": False
    },
    # Focus MIT Task (Mục tiêu quan trọng trong ngày)
    "focus_task": {
        "enabled": False,
        "text": "🎯 Hoàn thành công việc trước 17h45",
        "done": False
    },
    # Milestone & Payday Countdown (Đếm ngược ngày lương & Lễ)
    "payday_day": 5,
    # System Monitor (CPU & RAM)
    "show_sys_monitor": False,
    # Auto-Hide on edge (Tự thu gọn vào mép màn hình khi rời chuột)
    "auto_hide": False,
    # Weather Forecast (Dự báo thời tiết Open-Meteo)
    "weather": {
        "enabled": True,
        "city_name": "Hà Nội",
        "lat": 21.0285,
        "lon": 105.8542,
        "auto_refresh_min": 30
    },
    # Ambient Focus Sounds (Âm thanh tập trung / White Noise)
    "focus_sound": {
        "enabled": False,
        "sound_type": "rain"
    }
}


# ==========================================
# 🔔 ALARM / TIMER ALERT DIALOG
# ==========================================
class AlertNotificationDialog(tk.Toplevel):
    def __init__(self, master, title_text, message_text, on_dismiss=None, on_snooze=None, on_restart=None):
        super().__init__(master)
        self.title(title_text)
        self.attributes("-topmost", True)
        self.configure(bg="#151922")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.dismiss)

        self.on_dismiss = on_dismiss
        self.on_snooze = on_snooze
        self.on_restart = on_restart

        w, h = 440, 250
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        container = tk.Frame(self, bg="#151922", padx=20, pady=16)
        container.pack(fill="both", expand=True)

        lbl_icon = tk.Label(container, text="🔔 ⏰ 🔔", font=("Segoe UI Emoji", 24), bg="#151922", fg="#F59E0B")
        lbl_icon.pack(pady=(0, 6))

        self.lbl_msg = tk.Label(
            container,
            text=message_text,
            font=("Segoe UI", 12, "bold"),
            bg="#151922",
            fg="#F8FAFC",
            wraplength=400,
            justify="center"
        )
        self.lbl_msg.pack(pady=(0, 16))

        btn_frame = tk.Frame(container, bg="#151922")
        btn_frame.pack(fill="x", side="bottom")

        btn_dismiss = tk.Button(
            btn_frame,
            text="🔕 Tắt chuông",
            font=("Segoe UI", 10, "bold"),
            bg="#EF4444",
            fg="#FFFFFF",
            activebackground="#DC2626",
            activeforeground="#FFFFFF",
            relief="flat",
            padx=12,
            pady=8,
            cursor="hand2",
            command=self.dismiss
        )
        btn_dismiss.pack(side="left", expand=True, fill="x", padx=4)

        if on_snooze:
            btn_snooze = tk.Button(
                btn_frame,
                text="💤 Báo lại 5p",
                font=("Segoe UI", 10, "bold"),
                bg="#3B82F6",
                fg="#FFFFFF",
                activebackground="#2563EB",
                activeforeground="#FFFFFF",
                relief="flat",
                padx=10,
                pady=8,
                cursor="hand2",
                command=self.snooze
            )
            btn_snooze.pack(side="left", expand=True, fill="x", padx=4)

        if on_restart:
            btn_restart = tk.Button(
                btn_frame,
                text="🔄 Lặp lại",
                font=("Segoe UI", 10, "bold"),
                bg="#10B981",
                fg="#FFFFFF",
                activebackground="#059669",
                activeforeground="#FFFFFF",
                relief="flat",
                padx=10,
                pady=8,
                cursor="hand2",
                command=self.restart
            )
            btn_restart.pack(side="left", expand=True, fill="x", padx=4)

        self.flash_state = False
        self.bind("<Escape>", lambda e: self.dismiss())
        self.bind("<Return>", lambda e: self.dismiss())
        self.bind("<space>", lambda e: self.dismiss())

    def _flash(self):
        self.flash_state = not self.flash_state
        fg = "#EF4444" if self.flash_state else "#F59E0B"
        self.lbl_msg.configure(fg=fg)
        self.flash_timer = self.after(400, self._flash)

    def dismiss(self):
        sound_mgr.stop_alarm()
        if self.flash_timer:
            self.after_cancel(self.flash_timer)
        if self.on_dismiss:
            self.on_dismiss()
        self.destroy()

    def snooze(self):
        sound_mgr.stop_alarm()
        if self.flash_timer:
            self.after_cancel(self.flash_timer)
        if self.on_snooze:
            self.on_snooze()
        self.destroy()

    def restart(self):
        sound_mgr.stop_alarm()
        if self.flash_timer:
            self.after_cancel(self.flash_timer)
        if self.on_restart:
            self.on_restart()
        self.destroy()


# ==========================================
# 💧 HYDRATION & HEALTH REMINDER DIALOG
# ==========================================
class HydrationReminderDialog(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("💧 Nhắc Nhở Sức Khỏe")
        self.attributes("-topmost", True)
        self.configure(bg="#0f172a")
        self.resizable(False, False)

        w, h = 380, 200
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        container = tk.Frame(self, bg="#0f172a", padx=16, pady=14)
        container.pack(fill="both", expand=True)

        tk.Label(container, text="💧 🤸 👁️", font=("Segoe UI Emoji", 24), bg="#0f172a", fg="#38BDF8").pack(pady=(0, 4))
        tk.Label(container, text="UỐNG NƯỚC & VƯƠN VAI NÀO FEN!", font=("Segoe UI", 11, "bold"), bg="#0f172a", fg="#38BDF8").pack(pady=(0, 4))
        tk.Label(
            container,
            text="Ngồi máy tính lâu rồi, uống 1 ngụm nước, chớp mắt và đứng dậy xoay cổ tay vươn vai xíu nhé!",
            font=("Segoe UI", 9),
            bg="#0f172a",
            fg="#94A3B8",
            wraplength=340,
            justify="center"
        ).pack(pady=(0, 12))

        btn = tk.Button(
            container,
            text="✨ Đã uống nước & khỏe re!",
            font=("Segoe UI", 10, "bold"),
            bg="#0284C7",
            fg="#FFFFFF",
            activebackground="#0369A1",
            activeforeground="#FFFFFF",
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self.destroy
        )
        btn.pack()

        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<Return>", lambda e: self.destroy())
        self.bind("<space>", lambda e: self.destroy())


# ==========================================
# 🌦️ WEATHER FORECAST DIALOG
# ==========================================
class WeatherForecastDialog(tk.Toplevel):
    def __init__(self, master_app):
        super().__init__(master_app.root)
        self.app = master_app
        self.title("🌦️ Dự Báo Thời Tiết (Open-Meteo Realtime)")
        self.attributes("-topmost", True)
        self.configure(bg="#0f172a")
        self.resizable(False, False)

        w, h = 460, 320
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        container = tk.Frame(self, bg="#0f172a", padx=16, pady=14)
        container.pack(fill="both", expand=True)

        tk.Label(container, text="🌦️ THỜI TIẾT HIỆN TẠI & DỰ BÁO", font=("Segoe UI", 12, "bold"), bg="#0f172a", fg="#38BDF8").pack(anchor="w", pady=(0, 4))
        tk.Label(container, text="Dữ liệu thời gian thực từ trạm khí tượng thủy văn Open-Meteo", font=("Segoe UI", 8), bg="#0f172a", fg="#94A3B8").pack(anchor="w", pady=(0, 10))

        # City Selector Box
        sel_frame = tk.Frame(container, bg="#1e2430", padx=10, pady=8, relief="groove", bd=1)
        sel_frame.pack(fill="x", pady=(0, 12))

        tk.Label(sel_frame, text="Khu vực / Tỉnh thành:", font=("Segoe UI", 9, "bold"), bg="#1e2430", fg="#F8FAFC").pack(side="left", padx=(0, 6))

        cities = list(CITY_COORDINATES.keys())
        curr_city = self.app.config.get("weather", {}).get("city_name", "Hà Nội")
        self.cmb_city = ttk.Combobox(sel_frame, values=cities, state="readonly", width=16, font=("Segoe UI", 9))
        if curr_city in cities:
            self.cmb_city.current(cities.index(curr_city))
        else:
            self.cmb_city.current(0)
        self.cmb_city.pack(side="left", padx=(0, 6))

        btn_refresh = tk.Button(
            sel_frame,
            text="🔄 Cập nhật",
            font=("Segoe UI", 8, "bold"),
            bg="#2563EB",
            fg="#FFFFFF",
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=self.update_weather_data
        )
        btn_refresh.pack(side="left")

        # Weather details display card
        self.card = tk.Frame(container, bg="#111827", padx=14, pady=12, relief="groove", bd=1)
        self.card.pack(fill="both", expand=True, pady=(0, 10))

        self.lbl_icon = tk.Label(self.card, text="☀️", font=("Segoe UI Emoji", 32), bg="#111827", fg="#F59E0B")
        self.lbl_icon.pack(side="left", padx=(6, 16))

        info_box = tk.Frame(self.card, bg="#111827")
        info_box.pack(side="left", fill="both", expand=True)

        self.lbl_temp = tk.Label(info_box, text="--°C", font=("Segoe UI", 20, "bold"), bg="#111827", fg="#F8FAFC")
        self.lbl_temp.pack(anchor="w")

        self.lbl_desc = tk.Label(info_box, text="Đang tải dữ liệu thời tiết...", font=("Segoe UI", 10), bg="#111827", fg="#38BDF8")
        self.lbl_desc.pack(anchor="w", pady=1)

        self.lbl_wind = tk.Label(info_box, text="Gió: -- km/h", font=("Segoe UI", 9), bg="#111827", fg="#94A3B8")
        self.lbl_wind.pack(anchor="w", pady=1)

        btn_close = tk.Button(
            container,
            text="Đóng (Esc)",
            font=("Segoe UI", 9),
            bg="#334155",
            fg="#FFFFFF",
            relief="flat",
            padx=12,
            pady=5,
            cursor="hand2",
            command=self.destroy
        )
        btn_close.pack(side="right")

        self.bind("<Escape>", lambda e: self.destroy())
        self.update_weather_data()

    def update_weather_data(self):
        sel_city = self.cmb_city.get()
        self.app.config.setdefault("weather", {})
        self.app.config["weather"]["city_name"] = sel_city
        self.app.save_config()

        def _on_fetched(txt, data):
            if data:
                self.lbl_icon.configure(text=data.get("icon", "🌤️"))
                self.lbl_temp.configure(text=f"{data.get('temp', 0):.1f}°C")
                self.lbl_desc.configure(text=f"{data.get('desc', '')} ({data.get('city', '')})")
                self.lbl_wind.configure(text=f"💨 Tốc độ gió: {data.get('wind', 0)} km/h")

        self.app.weather_mgr.fetch_weather(callback=_on_fetched)


# ==========================================
# 🎯 QUICK TASK / MIT DIALOG
# ==========================================
class QuickTaskDialog(tk.Toplevel):
    def __init__(self, master_app):
        super().__init__(master_app.root)
        self.app = master_app
        self.title("🎯 Mục Tiêu Quan Trọng Trong Ngày (Focus MIT)")
        self.attributes("-topmost", True)
        self.configure(bg="#11141c")
        self.resizable(False, False)

        w, h = 460, 220
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        f = tk.Frame(self, bg="#11141c", padx=16, pady=14)
        f.pack(fill="both", expand=True)

        tk.Label(f, text="🎯 TASK QUAN TRỌNG NHẤT HÔM NAY", font=("Segoe UI", 11, "bold"), bg="#11141c", fg="#38BDF8").pack(anchor="w", pady=(0, 4))
        tk.Label(f, text="Giữ 1 mục tiêu duy nhất hiển thị cạnh đồng hồ để chống xao nhãng.", font=("Segoe UI", 8), bg="#11141c", fg="#94A3B8").pack(anchor="w", pady=(0, 10))

        self.ent_task = tk.Entry(f, font=("Segoe UI", 10), bg="#1e2430", fg="#F8FAFC", insertbackground="#fff", relief="flat", highlightthickness=1, highlightbackground="#334155")
        self.ent_task.pack(fill="x", pady=(0, 8), ipady=4)
        curr_task = self.app.config.get("focus_task", {}).get("text", "")
        self.ent_task.insert(0, curr_task)
        self.ent_task.focus_set()

        self.var_enable = tk.BooleanVar(value=self.app.config.get("focus_task", {}).get("enabled", True))
        chk = tk.Checkbutton(
            f,
            text="Hiển thị Task này trên đồng hồ",
            variable=self.var_enable,
            font=("Segoe UI", 9),
            bg="#11141c",
            fg="#FCD34D",
            selectcolor="#1e2430",
            activebackground="#11141c",
            activeforeground="#FCD34D"
        )
        chk.pack(anchor="w", pady=(0, 10))

        btn_box = tk.Frame(f, bg="#11141c")
        btn_box.pack(fill="x")

        btn_save = tk.Button(
            btn_box,
            text="💾 Lưu Task",
            font=("Segoe UI", 9, "bold"),
            bg="#2563EB",
            fg="#FFFFFF",
            relief="flat",
            padx=14,
            pady=5,
            cursor="hand2",
            command=self.save_task
        )
        btn_save.pack(side="left", padx=(0, 6))

        btn_clear = tk.Button(
            btn_box,
            text="🗑️ Xóa / Hoàn thành",
            font=("Segoe UI", 9),
            bg="#334155",
            fg="#FFFFFF",
            relief="flat",
            padx=10,
            pady=5,
            cursor="hand2",
            command=self.clear_task
        )
        btn_clear.pack(side="left")

        self.bind("<Return>", lambda e: self.save_task())
        self.bind("<Escape>", lambda e: self.destroy())

    def save_task(self):
        txt = self.ent_task.get().strip()
        self.app.config.setdefault("focus_task", {})
        self.app.config["focus_task"]["text"] = txt
        self.app.config["focus_task"]["enabled"] = self.var_enable.get() and bool(txt)
        self.app.save_config()
        self.app.update_extra_info_visibility()
        self.destroy()

    def clear_task(self):
        self.app.config.setdefault("focus_task", {})
        self.app.config["focus_task"]["text"] = ""
        self.app.config["focus_task"]["enabled"] = False
        self.app.save_config()
        self.app.update_extra_info_visibility()
        self.destroy()


# ==========================================
# 🎛️ CONTROL CENTER & SETTINGS DIALOG
# ==========================================
class ControlCenterDialog(tk.Toplevel):
    def __init__(self, master_app):
        super().__init__(master_app.root)
        self.app = master_app
        self.title("Bảng Điều Khiển & Cài Đặt Đồng Hồ (Control Center)")
        self.attributes("-topmost", True)
        self.configure(bg="#11141c")
        self.resizable(False, False)

        w, h = 820, 680
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        self.bind("<Escape>", lambda e: self.destroy())

        self._create_ui()

    def _create_ui(self):
        header = tk.Frame(self, bg="#181e2b", padx=16, pady=10)
        header.pack(fill="x")

        lbl_head = tk.Label(
            header,
            text="⚙️ BẢNG ĐIỀU KHIỂN & CÀI ĐẶT ĐỒNG HỒ",
            font=("Segoe UI", 12, "bold"),
            bg="#181e2b",
            fg="#00FFCC"
        )
        lbl_head.pack(side="left")

        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("TNotebook", background="#11141c", borderwidth=0)
        style.configure("TNotebook.Tab", background="#1c2331", foreground="#94a3b8", padding=[6, 5], font=("Segoe UI", 9, "bold"))
        style.map("TNotebook.Tab", background=[("selected", "#2563eb")], foreground=[("selected", "#ffffff")])

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=10)

        # Tabs
        self.tab_target = tk.Frame(self.notebook, bg="#151a24", padx=16, pady=10)
        self.tab_salary = tk.Frame(self.notebook, bg="#151a24", padx=16, pady=10)
        self.tab_weather = tk.Frame(self.notebook, bg="#151a24", padx=16, pady=10)
        self.tab_focus_sound = tk.Frame(self.notebook, bg="#151a24", padx=16, pady=10)
        self.tab_milestones = tk.Frame(self.notebook, bg="#151a24", padx=16, pady=10)
        self.tab_timer = tk.Frame(self.notebook, bg="#151a24", padx=16, pady=10)
        self.tab_alarm = tk.Frame(self.notebook, bg="#151a24", padx=16, pady=10)
        self.tab_stopwatch = tk.Frame(self.notebook, bg="#151a24", padx=16, pady=10)
        self.tab_pomodoro = tk.Frame(self.notebook, bg="#151a24", padx=16, pady=10)
        self.tab_display = tk.Frame(self.notebook, bg="#151a24", padx=16, pady=10)

        self.notebook.add(self.tab_target, text="🎯 Tan làm")
        self.notebook.add(self.tab_salary, text="💸 Tiền lương")
        self.notebook.add(self.tab_weather, text="🌦️ Thời tiết")
        self.notebook.add(self.tab_focus_sound, text="🎧 Âm thanh")
        self.notebook.add(self.tab_milestones, text="📅 Dịp lễ")
        self.notebook.add(self.tab_timer, text="⏳ Đếm ngược")
        self.notebook.add(self.tab_alarm, text="⏰ Báo thức")
        self.notebook.add(self.tab_stopwatch, text="⏱️ Bấm giờ")
        self.notebook.add(self.tab_pomodoro, text="🍅 Pomodoro")
        self.notebook.add(self.tab_display, text="🎨 Giao diện")

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

        mode_map = {
            "target_time": 0,
            "salary": 1,
            "milestone": 2,
            "timer": 3,
            "alarm": 4,
            "stopwatch": 5,
            "pomodoro": 6,
            "clock": 7
        }
        idx = mode_map.get(self.app.config.get("mode", "clock"), 0)
        self.notebook.select(idx)

    # ---------------- 🎯 TAB TARGET TIME & WORK DEPARTURE ----------------
    def _setup_target_tab(self):
        f = self.tab_target

        tk.Label(f, text="🎯 ĐẾM NGƯỢC TAN LÀM & MỐC GIỜ MỤC TIÊU", font=("Segoe UI", 11, "bold"), bg="#151a24", fg="#F59E0B").pack(anchor="w", pady=(0, 4))

        sched_box = tk.LabelFrame(f, text=" 🏢 CẤU HÌNH GIỜ TAN LÀM THEO THỨ (T2 - T6 & THỨ 7) ", font=("Segoe UI", 9, "bold"), bg="#1e2430", fg="#38BDF8", padx=12, pady=8)
        sched_box.pack(fill="x", pady=(0, 10))

        work_cfg = self.app.config.get("work_departure", {
            "start_time": "08:30",
            "mon_fri_time": "17:45",
            "sat_time": "16:00",
            "auto_schedule": True
        })

        row0 = tk.Frame(sched_box, bg="#1e2430")
        row0.pack(fill="x", pady=2)
        tk.Label(row0, text="• Giờ bắt đầu làm việc:", font=("Segoe UI", 9), bg="#1e2430", fg="#cbd5e1", width=24, anchor="w").pack(side="left")
        self.ent_start_time = tk.Entry(row0, font=("Consolas", 10), width=8, bg="#0f172a", fg="#38BDF8", insertbackground="#fff", justify="center")
        self.ent_start_time.pack(side="left", padx=6)
        self.ent_start_time.insert(0, work_cfg.get("start_time", "08:30"))
        tk.Label(row0, text="(Để tính % thanh tiến độ trong ngày)", font=("Segoe UI", 8), bg="#1e2430", fg="#94a3b8").pack(side="left")

        row1 = tk.Frame(sched_box, bg="#1e2430")
        row1.pack(fill="x", pady=2)
        tk.Label(row1, text="• Thứ 2 đến Thứ 6 (T2-T6):", font=("Segoe UI", 9, "bold"), bg="#1e2430", fg="#e2e8f0", width=24, anchor="w").pack(side="left")
        self.ent_mon_fri = tk.Entry(row1, font=("Consolas", 10, "bold"), width=8, bg="#0f172a", fg="#F59E0B", insertbackground="#fff", justify="center")
        self.ent_mon_fri.pack(side="left", padx=6)
        self.ent_mon_fri.insert(0, work_cfg.get("mon_fri_time", "17:45"))
        tk.Label(row1, text="(Mặc định: 17:45)", font=("Segoe UI", 8), bg="#1e2430", fg="#94a3b8").pack(side="left")

        row2 = tk.Frame(sched_box, bg="#1e2430")
        row2.pack(fill="x", pady=2)
        tk.Label(row2, text="• Riêng Thứ 7 (Về sớm):", font=("Segoe UI", 9, "bold"), bg="#1e2430", fg="#4ade80", width=24, anchor="w").pack(side="left")
        self.ent_sat = tk.Entry(row2, font=("Consolas", 10, "bold"), width=8, bg="#0f172a", fg="#4ade80", insertbackground="#fff", justify="center")
        self.ent_sat.pack(side="left", padx=6)
        self.ent_sat.insert(0, work_cfg.get("sat_time", "16:00"))
        tk.Label(row2, text="(Mặc định: 16:00)", font=("Segoe UI", 8), bg="#1e2430", fg="#94a3b8").pack(side="left")

        row_lunch = tk.Frame(sched_box, bg="#1e2430")
        row_lunch.pack(fill="x", pady=2)
        tk.Label(row_lunch, text="• Giờ nghỉ trưa (Lunch):", font=("Segoe UI", 9, "bold"), bg="#1e2430", fg="#FCD34D", width=24, anchor="w").pack(side="left")
        self.ent_lunch_start = tk.Entry(row_lunch, font=("Consolas", 10, "bold"), width=6, bg="#0f172a", fg="#FCD34D", insertbackground="#fff", justify="center")
        self.ent_lunch_start.pack(side="left", padx=(6, 2))
        self.ent_lunch_start.insert(0, work_cfg.get("lunch_start", "12:00"))
        tk.Label(row_lunch, text="đến", font=("Segoe UI", 8), bg="#1e2430", fg="#cbd5e1").pack(side="left", padx=4)
        self.ent_lunch_end = tk.Entry(row_lunch, font=("Consolas", 10, "bold"), width=6, bg="#0f172a", fg="#FCD34D", insertbackground="#fff", justify="center")
        self.ent_lunch_end.pack(side="left", padx=(2, 6))
        self.ent_lunch_end.insert(0, work_cfg.get("lunch_end", "13:15"))
        tk.Label(row_lunch, text="(Tạm dừng nhảy lương)", font=("Segoe UI", 8), bg="#1e2430", fg="#94a3b8").pack(side="left")

        btn_save_sched = tk.Button(
            sched_box,
            text="💾 Lưu cấu hình giờ làm & nghỉ trưa",
            font=("Segoe UI", 9, "bold"),
            bg="#2563eb",
            fg="#ffffff",
            relief="flat",
            padx=10,
            pady=3,
            cursor="hand2",
            command=self._save_work_schedule
        )
        btn_save_sched.pack(anchor="e", pady=(4, 0))

        now = datetime.now()
        today_dep, today_tag = self.app.get_today_departure_info(now)
        self.btn_today_dep = tk.Button(
            f,
            text=f"🏢 ĐẾM NGƯỢC TAN LÀM HÔM NAY ({today_tag}: {today_dep[:5]})",
            font=("Segoe UI", 11, "bold"),
            bg="#10B981",
            fg="#FFFFFF",
            activebackground="#059669",
            activeforeground="#FFFFFF",
            relief="flat",
            pady=8,
            cursor="hand2",
            command=self._start_today_departure
        )
        self.btn_today_dep.pack(fill="x", pady=(0, 10))

        custom_box = tk.LabelFrame(f, text=" 🎯 HOẶC ĐẶT MỐC GIỜ TÙY CHỌN TRONG NGÀY ", font=("Segoe UI", 9, "bold"), bg="#1e2430", fg="#cbd5e1", padx=12, pady=8)
        custom_box.pack(fill="x")

        row_c1 = tk.Frame(custom_box, bg="#1e2430")
        row_c1.pack(fill="x", pady=2)

        tk.Label(row_c1, text="Mốc giờ:", font=("Segoe UI", 9, "bold"), bg="#1e2430", fg="#e2e8f0").pack(side="left", padx=(0, 6))
        self.spin_tgt_h = tk.Spinbox(row_c1, from_=0, to=23, width=3, font=("Consolas", 11, "bold"), bg="#0f172a", fg="#F59E0B", justify="center", buttonbackground="#334155")
        self.spin_tgt_h.pack(side="left")
        self.spin_tgt_h.delete(0, "end")
        self.spin_tgt_h.insert(0, "17")

        tk.Label(row_c1, text=" : ", bg="#1e2430", fg="#94a3b8", font=("Consolas", 11, "bold")).pack(side="left")

        self.spin_tgt_m = tk.Spinbox(row_c1, from_=0, to=59, width=3, font=("Consolas", 11, "bold"), bg="#0f172a", fg="#F59E0B", justify="center", buttonbackground="#334155")
        self.spin_tgt_m.pack(side="left")
        self.spin_tgt_m.delete(0, "end")
        self.spin_tgt_m.insert(0, "45")

        tk.Label(row_c1, text="Tên sự kiện:", font=("Segoe UI", 9, "bold"), bg="#1e2430", fg="#e2e8f0").pack(side="left", padx=(12, 6))
        self.ent_tgt_label = tk.Entry(row_c1, font=("Segoe UI", 9), bg="#0f172a", fg="#ffffff", insertbackground="#ffffff", width=14)
        self.ent_tgt_label.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.ent_tgt_label.insert(0, "Tan làm")

        btn_apply_custom_tgt = tk.Button(
            row_c1,
            text="Bắt đầu",
            font=("Segoe UI", 9, "bold"),
            bg="#F59E0B",
            fg="#111827",
            relief="flat",
            padx=10,
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

    # ---------------- 💸 TAB SALARY & TASK ----------------
    def _setup_salary_tab(self):
        f = self.tab_salary
        sal_cfg = self.app.config.get("salary", {
            "enabled": False,
            "show_daily": True,
            "show_monthly": True,
            "monthly": 15000000,
            "work_days": 22,
            "work_hours": 8.0,
            "hidden": False
        })
        work_cfg = self.app.config.get("work_departure", {
            "start_time": "08:30",
            "mon_fri_time": "17:45",
            "sat_time": "16:00",
            "lunch_start": "12:00",
            "lunch_end": "13:15"
        })
        task_cfg = self.app.config.get("focus_task", {
            "enabled": False,
            "text": "🎯 Hoàn thành công việc trước 17h45",
            "done": False
        })

        tk.Label(f, text="💸 BỘ ĐẾM TIỀN LƯƠNG 2 DÒNG (NGÀY & THÁNG) & TASK TRỌNG TÂM", font=("Segoe UI", 11, "bold"), bg="#151a24", fg="#34D399").pack(anchor="w", pady=(0, 6))

        sal_box = tk.LabelFrame(f, text=" 💸 THIẾT LẬP BỘ ĐẾM TIỀN LƯƠNG NHẢY THEO GIÂY ", font=("Segoe UI", 9, "bold"), bg="#1e2430", fg="#34D399", padx=12, pady=8)
        sal_box.pack(fill="x", pady=(0, 10))

        row1 = tk.Frame(sal_box, bg="#1e2430")
        row1.pack(fill="x", pady=3)
        tk.Label(row1, text="• Lương tháng (VNĐ):", font=("Segoe UI", 9, "bold"), bg="#1e2430", fg="#e2e8f0", width=22, anchor="w").pack(side="left")
        self.ent_salary_monthly = tk.Entry(row1, font=("Consolas", 10, "bold"), width=14, bg="#0f172a", fg="#34D399", insertbackground="#fff", justify="center")
        self.ent_salary_monthly.pack(side="left", padx=6)
        self.ent_salary_monthly.insert(0, str(int(sal_cfg.get("monthly", 15000000))))
        tk.Label(row1, text="VNĐ / Tháng", font=("Segoe UI", 8), bg="#1e2430", fg="#94a3b8").pack(side="left")

        row2 = tk.Frame(sal_box, bg="#1e2430")
        row2.pack(fill="x", pady=3)
        tk.Label(row2, text="• Số ngày làm / tháng:", font=("Segoe UI", 9), bg="#1e2430", fg="#cbd5e1", width=22, anchor="w").pack(side="left")
        self.ent_sal_days = tk.Entry(row2, font=("Consolas", 10), width=6, bg="#0f172a", fg="#fff", insertbackground="#fff", justify="center")
        self.ent_sal_days.pack(side="left", padx=6)
        self.ent_sal_days.insert(0, str(sal_cfg.get("work_days", 22)))

        tk.Label(row2, text="• Giờ làm / ngày:", font=("Segoe UI", 9), bg="#1e2430", fg="#cbd5e1", padx=10).pack(side="left")
        self.ent_sal_hours = tk.Entry(row2, font=("Consolas", 10), width=6, bg="#0f172a", fg="#fff", insertbackground="#fff", justify="center")
        self.ent_sal_hours.pack(side="left", padx=6)
        self.ent_sal_hours.insert(0, str(sal_cfg.get("work_hours", 8.0)))

        row3 = tk.Frame(sal_box, bg="#1e2430")
        row3.pack(fill="x", pady=3)
        tk.Label(row3, text="• Nghỉ trưa từ:", font=("Segoe UI", 9), bg="#1e2430", fg="#cbd5e1", width=22, anchor="w").pack(side="left")
        self.ent_sal_lunch_start = tk.Entry(row3, font=("Consolas", 10), width=6, bg="#0f172a", fg="#FCD34D", insertbackground="#fff", justify="center")
        self.ent_sal_lunch_start.pack(side="left", padx=6)
        self.ent_sal_lunch_start.insert(0, work_cfg.get("lunch_start", "12:00"))
        tk.Label(row3, text="đến:", font=("Segoe UI", 9), bg="#1e2430", fg="#cbd5e1", padx=4).pack(side="left")
        self.ent_sal_lunch_end = tk.Entry(row3, font=("Consolas", 10), width=6, bg="#0f172a", fg="#FCD34D", insertbackground="#fff", justify="center")
        self.ent_sal_lunch_end.pack(side="left", padx=6)
        self.ent_sal_lunch_end.insert(0, work_cfg.get("lunch_end", "13:15"))
        tk.Label(row3, text="(Tạm dừng tính lương)", font=("Segoe UI", 8), bg="#1e2430", fg="#94a3b8").pack(side="left", padx=4)

        cycle_box = tk.Frame(sal_box, bg="#1e2430")
        cycle_box.pack(fill="x", pady=(4, 4))

        row_c_head = tk.Frame(cycle_box, bg="#1e2430")
        row_c_head.pack(fill="x", pady=(0, 2))
        tk.Label(row_c_head, text="• Chu kỳ tính lương tháng:", font=("Segoe UI", 9, "bold"), bg="#1e2430", fg="#38BDF8").pack(side="left")

        self.var_sal_cycle = tk.StringVar(value=sal_cfg.get("calc_cycle", "calendar_month"))

        rb_box = tk.Frame(cycle_box, bg="#1e2430")
        rb_box.pack(fill="x", padx=(16, 0))

        rb1 = tk.Radiobutton(
            rb_box,
            text="📅 Từ ngày 01 đầu tháng dương lịch (Mặc định)",
            variable=self.var_sal_cycle,
            value="calendar_month",
            font=("Segoe UI", 9),
            bg="#1e2430",
            fg="#F8FAFC",
            selectcolor="#0f172a",
            activebackground="#1e2430",
            activeforeground="#38BDF8"
        )
        rb1.pack(anchor="w", pady=1)

        rb2 = tk.Radiobutton(
            rb_box,
            text="💸 Từ ngày nhận lương tháng trước (Sau ngày Ting Ting hàng tháng)",
            variable=self.var_sal_cycle,
            value="payday_cycle",
            font=("Segoe UI", 9),
            bg="#1e2430",
            fg="#FCD34D",
            selectcolor="#0f172a",
            activebackground="#1e2430",
            activeforeground="#FCD34D"
        )
        rb2.pack(anchor="w", pady=1)

        row_payday = tk.Frame(sal_box, bg="#1e2430")
        row_payday.pack(fill="x", pady=(4, 2))
        tk.Label(row_payday, text="• Ngày nhận lương (Ting Ting):", font=("Segoe UI", 9, "bold"), bg="#1e2430", fg="#34D399", width=24, anchor="w").pack(side="left")
        self.spin_sal_payday = tk.Spinbox(row_payday, from_=1, to=31, width=4, font=("Consolas", 10, "bold"), bg="#0f172a", fg="#34D399", justify="center", buttonbackground="#334155")
        self.spin_sal_payday.pack(side="left", padx=6)
        self.spin_sal_payday.delete(0, "end")
        self.spin_sal_payday.insert(0, str(self.app.config.get("payday_day", 5)))
        tk.Label(row_payday, text="(Hàng tháng, ví dụ: 5, 10, 15)", font=("Segoe UI", 8), bg="#1e2430", fg="#94a3b8").pack(side="left", padx=4)

        self.var_sal_enabled = tk.BooleanVar(value=sal_cfg.get("enabled", False))
        chk_sal = tk.Checkbutton(
            sal_box,
            text="Bật bộ đếm tiền lương nhảy theo thời gian thực",
            variable=self.var_sal_enabled,
            font=("Segoe UI", 9, "bold"),
            bg="#1e2430",
            fg="#FCD34D",
            selectcolor="#0f172a",
            activebackground="#1e2430",
            activeforeground="#FCD34D"
        )
        chk_sal.pack(anchor="w", pady=(6, 2))

        self.var_sal_show_daily = tk.BooleanVar(value=sal_cfg.get("show_daily", True))
        chk_sal_d = tk.Checkbutton(
            sal_box,
            text="☀️ Hiển thị Dòng 1: Lương hôm nay (Theo ngày: 💸 Ngày: +125.430 đ)",
            variable=self.var_sal_show_daily,
            font=("Segoe UI", 9),
            bg="#1e2430",
            fg="#34D399",
            selectcolor="#0f172a",
            activebackground="#1e2430",
            activeforeground="#34D399"
        )
        chk_sal_d.pack(anchor="w", pady=1)

        self.var_sal_show_monthly = tk.BooleanVar(value=sal_cfg.get("show_monthly", True))
        chk_sal_m = tk.Checkbutton(
            sal_box,
            text="📅 Hiển thị Dòng 2: Lương tích lũy trong tháng (Theo tháng: 📅 Tháng: 4.825.430 đ - 32.1%)",
            variable=self.var_sal_show_monthly,
            font=("Segoe UI", 9),
            bg="#1e2430",
            fg="#6EE7B7",
            selectcolor="#0f172a",
            activebackground="#1e2430",
            activeforeground="#6EE7B7"
        )
        chk_sal_m.pack(anchor="w", pady=1)

        self.var_sal_hidden = tk.BooleanVar(value=sal_cfg.get("hidden", False))
        chk_sal_hid = tk.Checkbutton(
            sal_box,
            text="Che giấu số tiền (Hiện •••••• đ để tránh người ngoài nhìn) [Phím S]",
            variable=self.var_sal_hidden,
            font=("Segoe UI", 9),
            bg="#1e2430",
            fg="#94A3B8",
            selectcolor="#0f172a",
            activebackground="#1e2430",
            activeforeground="#94A3B8"
        )
        chk_sal_hid.pack(anchor="w", pady=2)

        # Task Box
        task_box = tk.LabelFrame(f, text=" 🎯 TASK TRỌNG TÂM TRONG NGÀY (SINGLE MIT) ", font=("Segoe UI", 9, "bold"), bg="#1e2430", fg="#38BDF8", padx=12, pady=8)
        task_box.pack(fill="x", pady=(0, 8))

        row_t = tk.Frame(task_box, bg="#1e2430")
        row_t.pack(fill="x", pady=2)
        tk.Label(row_t, text="Task hôm nay:", font=("Segoe UI", 9, "bold"), bg="#1e2430", fg="#e2e8f0").pack(side="left", padx=(0, 6))
        self.ent_focus_task = tk.Entry(row_t, font=("Segoe UI", 9), bg="#0f172a", fg="#F8FAFC", insertbackground="#fff")
        self.ent_focus_task.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.ent_focus_task.insert(0, task_cfg.get("text", ""))

        self.var_task_enabled = tk.BooleanVar(value=task_cfg.get("enabled", False))
        chk_task = tk.Checkbutton(
            task_box,
            text="Hiển thị Task trọng tâm cạnh đồng hồ để nhắc việc [Phím T]",
            variable=self.var_task_enabled,
            font=("Segoe UI", 9),
            bg="#1e2430",
            fg="#38BDF8",
            selectcolor="#0f172a",
            activebackground="#1e2430",
            activeforeground="#38BDF8"
        )
        chk_task.pack(anchor="w", pady=2)

        btn_save_sal = tk.Button(
            f,
            text="💾 LƯU THIẾT LẬP TIỀN LƯƠNG & TASK",
            font=("Segoe UI", 11, "bold"),
            bg="#10B981",
            fg="#FFFFFF",
            activebackground="#059669",
            activeforeground="#FFFFFF",
            relief="flat",
            pady=8,
            cursor="hand2",
            command=self._save_salary_settings
        )
        btn_save_sal.pack(fill="x", pady=(10, 4))

    def _save_salary_settings(self):
        try:
            mon = float(self.ent_salary_monthly.get().replace(".", "").replace(",", "").strip())
            days = int(self.ent_sal_days.get().strip())
            hrs = float(self.ent_sal_hours.get().strip())
            ls = self.ent_sal_lunch_start.get().strip()
            le = self.ent_sal_lunch_end.get().strip()
            cyc = self.var_sal_cycle.get()
            task_txt = self.ent_focus_task.get().strip()

            for val, name in [(ls, "Nghỉ trưa bắt đầu"), (le, "Nghỉ trưa kết thúc")]:
                parts = val.split(":")
                if len(parts) != 2 or not (0 <= int(parts[0]) <= 23 and 0 <= int(parts[1]) <= 59):
                    raise ValueError(f"Giờ {name} không đúng định dạng HH:MM!")

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

            self.app.config.setdefault("work_departure", {})
            self.app.config["work_departure"]["lunch_start"] = ls
            self.app.config["work_departure"]["lunch_end"] = le

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
        w_cfg = self.app.config.get("weather", {
            "enabled": True,
            "city_name": "Hà Nội",
            "lat": 21.0285,
            "lon": 105.8542
        })

        tk.Label(f, text="🌦️ DỰ BÁO THỜI TIẾT REALTIME (OPEN-METEO)", font=("Segoe UI", 11, "bold"), bg="#151a24", fg="#38BDF8").pack(anchor="w", pady=(0, 6))

        box = tk.LabelFrame(f, text=" 🌤️ CẤU HÌNH THỜI TIẾT ", font=("Segoe UI", 9, "bold"), bg="#1e2430", fg="#38BDF8", padx=12, pady=10)
        box.pack(fill="x", pady=(0, 10))

        row1 = tk.Frame(box, bg="#1e2430")
        row1.pack(fill="x", pady=3)

        tk.Label(row1, text="• Khu vực / Tỉnh thành:", font=("Segoe UI", 9, "bold"), bg="#1e2430", fg="#cbd5e1", width=22, anchor="w").pack(side="left")
        cities = list(CITY_COORDINATES.keys())
        self.cmb_weather_city = ttk.Combobox(row1, values=cities, state="readonly", width=18, font=("Segoe UI", 9))
        curr_city = w_cfg.get("city_name", "Hà Nội")
        if curr_city in cities:
            self.cmb_weather_city.current(cities.index(curr_city))
        else:
            self.cmb_weather_city.current(0)
        self.cmb_weather_city.pack(side="left", padx=6)

        self.var_weather_enabled = tk.BooleanVar(value=w_cfg.get("enabled", True))
        chk_w = tk.Checkbutton(
            box,
            text="Hiển thị thời tiết trên màn hình đồng hồ (Ví dụ: 🌤️ Hà Nội: 31°C • Có mây)",
            variable=self.var_weather_enabled,
            font=("Segoe UI", 9, "bold"),
            bg="#1e2430",
            fg="#38BDF8",
            selectcolor="#0f172a",
            activebackground="#1e2430",
            activeforeground="#38BDF8"
        )
        chk_w.pack(anchor="w", pady=(8, 2))

        btn_box = tk.Frame(f, bg="#151a24")
        btn_box.pack(fill="x", pady=6)

        btn_save_w = tk.Button(
            btn_box,
            text="💾 Lưu & Cập nhật thời tiết",
            font=("Segoe UI", 10, "bold"),
            bg="#2563EB",
            fg="#FFFFFF",
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self._save_weather_settings
        )
        btn_save_w.pack(side="left", padx=(0, 8))

        btn_open_w_dialog = tk.Button(
            btn_box,
            text="🔍 Xem chi tiết thời tiết",
            font=("Segoe UI", 9),
            bg="#334155",
            fg="#FFFFFF",
            relief="flat",
            padx=10,
            pady=6,
            cursor="hand2",
            command=lambda: WeatherForecastDialog(self.app)
        )
        btn_open_w_dialog.pack(side="left")

    def _save_weather_settings(self):
        c_name = self.cmb_weather_city.get()
        self.app.config.setdefault("weather", {})
        self.app.config["weather"]["city_name"] = c_name
        self.app.config["weather"]["enabled"] = self.var_weather_enabled.get()
        self.app.save_config()
        self.app.weather_mgr.fetch_weather(callback=lambda txt, d: self.app.update_extra_info_visibility())
        self.app.update_extra_info_visibility()
        messagebox.showinfo("Thành công", f"Đã lưu cài đặt thời tiết khu vực: {c_name}!", parent=self)

    # ---------------- 🎧 TAB FOCUS SOUND ----------------
    def _setup_focus_sound_tab(self):
        f = self.tab_focus_sound
        fs_cfg = self.app.config.get("focus_sound", {
            "enabled": False,
            "sound_type": "rain"
        })

        tk.Label(f, text="🎧 ÂM THANH TẬP TRUNG & WHITE NOISE (FOCUS SOUNDS)", font=("Segoe UI", 11, "bold"), bg="#151a24", fg="#A78BFA").pack(anchor="w", pady=(0, 6))

        box = tk.LabelFrame(f, text=" 🎵 CHỌN LOẠI ÂM THANH TẬP TRUNG ", font=("Segoe UI", 9, "bold"), bg="#1e2430", fg="#A78BFA", padx=12, pady=10)
        box.pack(fill="x", pady=(0, 10))

        sound_types = [
            ("rain", "🌧️ Mưa Rơi Rả Rích (Rainfall Ambient)"),
            ("ocean", "🌊 Sóng Biển Dập Dềnh (Ocean Waves)"),
            ("brown_noise", "🧘 Tiếng Ồn Nâu Thư Thái (Brown Noise - Deep Focus)"),
            ("white_noise", "📻 Tiếng Ồn Trắng (White Noise - Chống xao nhãng)"),
            ("alpha_wave", "🧠 Sóng Não Tập Trung Alpha 432Hz (Binaural Beats)"),
            ("cafe", "☕ Quán Cafe & Lofi Ambient (Cafe Vibe)"),
        ]

        self.var_sound_type = tk.StringVar(value=fs_cfg.get("sound_type", "rain"))

        for s_id, s_name in sound_types:
            rb = tk.Radiobutton(
                box,
                text=s_name,
                value=s_id,
                variable=self.var_sound_type,
                font=("Segoe UI", 9),
                bg="#1e2430",
                fg="#F8FAFC",
                selectcolor="#0f172a",
                activebackground="#1e2430",
                activeforeground="#A78BFA",
                command=self._on_sound_type_changed
            )
            rb.pack(anchor="w", pady=2)

        ctrl_box = tk.Frame(f, bg="#151a24")
        ctrl_box.pack(fill="x", pady=6)

        self.btn_toggle_focus_sound = tk.Button(
            ctrl_box,
            text="⏹ DỪNG PHÁT ÂM THANH" if self.app.focus_sound_mgr.is_playing else "▶ BẬT ÂM THANH TẬP TRUNG",
            font=("Segoe UI", 11, "bold"),
            bg="#EF4444" if self.app.focus_sound_mgr.is_playing else "#8B5CF6",
            fg="#FFFFFF",
            relief="flat",
            pady=8,
            cursor="hand2",
            command=self._toggle_focus_sound_play
        )
        self.btn_toggle_focus_sound.pack(fill="x", pady=4)

        tk.Label(f, text="💡 Gợi ý: Bấm phím F9 bất cứ lúc nào để Bật / Tắt nhanh âm thanh tập trung!", font=("Segoe UI", 8, "italic"), bg="#151a24", fg="#94A3B8").pack(anchor="w", pady=(4, 0))

    def _on_sound_type_changed(self):
        st = self.var_sound_type.get()
        self.app.config.setdefault("focus_sound", {})
        self.app.config["focus_sound"]["sound_type"] = st
        self.app.save_config()
        if self.app.focus_sound_mgr.is_playing:
            self.app.focus_sound_mgr.play(st)

    def _toggle_focus_sound_play(self):
        st = self.var_sound_type.get()
        is_now_playing = self.app.focus_sound_mgr.toggle(st)
        if is_now_playing:
            self.btn_toggle_focus_sound.configure(text="⏹ DỪNG PHÁT ÂM THANH", bg="#EF4444")
        else:
            self.btn_toggle_focus_sound.configure(text="▶ BẬT ÂM THANH TẬP TRUNG", bg="#8B5CF6")

    # ---------------- 📅 TAB MILESTONES & PAYDAY ----------------
    def _setup_milestones_tab(self):
        f = self.tab_milestones

        tk.Label(f, text="🎆 ĐẾM NGƯỢC CÁC DỊP LỄ LỚN & MỐC QUAN TRỌNG", font=("Segoe UI", 11, "bold"), bg="#151a24", fg="#F59E0B").pack(anchor="w", pady=(0, 6))

        # Payday status banner
        now = datetime.now()
        p_day = self.app.config.get("payday_day", 5)
        rem_p_days, p_target_str = self.app.get_payday_countdown_info(now, p_day)
        pay_banner = tk.Frame(f, bg="#1e2430", padx=12, pady=10, relief="groove", bd=1)
        pay_banner.pack(fill="x", pady=(0, 10))

        tk.Label(
            pay_banner,
            text=f"💸 Đợt Ting Ting lương tiếp theo: Ngày {p_day} ({p_target_str}) — Còn {rem_p_days} ngày! 🎉",
            font=("Segoe UI", 10, "bold"),
            bg="#1e2430",
            fg="#34D399"
        ).pack(anchor="w")
        tk.Label(
            pay_banner,
            text="💡 Để đổi ngày nhận lương hàng tháng, bạn vào tab '💸 Tiền Lương & Task' để cài đặt.",
            font=("Segoe UI", 8, "italic"),
            bg="#1e2430",
            fg="#94A3B8"
        ).pack(anchor="w", pady=(2, 0))

        # Holidays list
        hol_box = tk.LabelFrame(f, text=" 🎆 CÁC DỊP LỄ LỚN TIẾP THEO ", font=("Segoe UI", 9, "bold"), bg="#1e2430", fg="#38BDF8", padx=12, pady=8)
        hol_box.pack(fill="both", expand=True)

        self.tree_milestones = ttk.Treeview(hol_box, columns=("event", "days", "date"), show="headings", height=6)
        self.tree_milestones.heading("event", text="Sự kiện / Dịp lễ")
        self.tree_milestones.heading("days", text="Còn lại")
        self.tree_milestones.heading("date", text="Ngày")
        self.tree_milestones.column("event", width=260)
        self.tree_milestones.column("days", width=100, anchor="center")
        self.tree_milestones.column("date", width=120, anchor="center")
        self.tree_milestones.pack(fill="both", expand=True, pady=4)

        self._populate_milestones_list()

    def _populate_milestones_list(self):
        for item in self.tree_milestones.get_children():
            self.tree_milestones.delete(item)

        now = datetime.now()
        events = [
            ("🎆 Tết Dương Lịch 2027", datetime(now.year + 1 if now.month == 12 else now.year, 1 if now.month < 12 else 1, 1)),
            ("🧧 Tết Nguyên Đán (Âm Lịch)", datetime(now.year + 1 if now.month >= 2 else now.year, 2, 17)),
            ("👑 Giỗ Tổ Hùng Vương (10/3 Âm)", datetime(now.year, 4, 26)),
            ("🇻🇳 Thống Nhất & Lao Động (30/4 - 1/5)", datetime(now.year if now.month < 5 else now.year + 1, 4, 30)),
            ("⭐ Quốc Khánh Việt Nam (2/9)", datetime(now.year if now.month < 9 else now.year + 1, 9, 2)),
            ("🎄 Lễ Giáng Sinh (Noel 25/12)", datetime(now.year if now.month < 12 or (now.month == 12 and now.day <= 25) else now.year + 1, 12, 25))
        ]

        for name, dt in sorted(events, key=lambda x: x[1]):
            if dt < now:
                dt = datetime(dt.year + 1, dt.month, dt.day)
            diff_d = int(math.ceil((dt - now).total_seconds() / 86400.0))
            self.tree_milestones.insert("", "end", values=(name, f"⏳ {diff_d} ngày", dt.strftime("%d/%m/%Y")))

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
                bg="#1e293b",
                fg="#e2e8f0",
                activebackground="#3b82f6",
                activeforeground="#ffffff",
                relief="flat",
                padx=8,
                pady=6,
                cursor="hand2",
                command=lambda s=sec: self._set_timer_preset(s)
            )
            btn.grid(row=row, column=col, padx=3, pady=3, sticky="nsew")
            col += 1
            if col > 3:
                col = 0
                row += 1
        for i in range(4):
            preset_frame.grid_columnconfigure(i, weight=1)

        custom_frame = tk.Frame(f, bg="#1e2430", padx=10, pady=8, relief="groove", bd=1)
        custom_frame.pack(fill="x", pady=(0, 12))

        tk.Label(custom_frame, text="Nhập tùy chỉnh:", font=("Segoe UI", 9, "bold"), bg="#1e2430", fg="#94a3b8").grid(row=0, column=0, padx=(0, 6))

        self.spin_timer_h = tk.Spinbox(custom_frame, from_=0, to=23, width=3, font=("Consolas", 11, "bold"), bg="#0f172a", fg="#38bdf8", justify="center", buttonbackground="#334155")
        self.spin_timer_h.grid(row=0, column=1)
        tk.Label(custom_frame, text="Giờ", bg="#1e2430", fg="#94a3b8", font=("Segoe UI", 8)).grid(row=0, column=2, padx=(2, 6))

        self.spin_timer_m = tk.Spinbox(custom_frame, from_=0, to=59, width=3, font=("Consolas", 11, "bold"), bg="#0f172a", fg="#38bdf8", justify="center", buttonbackground="#334155")
        self.spin_timer_m.grid(row=0, column=3)
        self.spin_timer_m.delete(0, "end")
        self.spin_timer_m.insert(0, str(self.app.timer_duration // 60 % 60))
        tk.Label(custom_frame, text="Phút", bg="#1e2430", fg="#94a3b8", font=("Segoe UI", 8)).grid(row=0, column=4, padx=(2, 6))

        self.spin_timer_s = tk.Spinbox(custom_frame, from_=0, to=59, width=3, font=("Consolas", 11, "bold"), bg="#0f172a", fg="#38bdf8", justify="center", buttonbackground="#334155")
        self.spin_timer_s.grid(row=0, column=5)
        self.spin_timer_s.delete(0, "end")
        self.spin_timer_s.insert(0, str(self.app.timer_duration % 60))
        tk.Label(custom_frame, text="Giây", bg="#1e2430", fg="#94a3b8", font=("Segoe UI", 8)).grid(row=0, column=6, padx=(2, 6))

        btn_apply_custom = tk.Button(
            custom_frame,
            text="Áp dụng",
            font=("Segoe UI", 9, "bold"),
            bg="#2563eb",
            fg="#ffffff",
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=self._apply_custom_timer
        )
        btn_apply_custom.grid(row=0, column=7, padx=6)

        action_frame = tk.Frame(f, bg="#151a24")
        action_frame.pack(fill="x", pady=4)

        self.btn_timer_toggle = tk.Button(
            action_frame,
            text="▶ BẮT ĐẦU ĐẾM",
            font=("Segoe UI", 11, "bold"),
            bg="#10B981",
            fg="#FFFFFF",
            relief="flat",
            padx=12,
            pady=8,
            cursor="hand2",
            command=self._toggle_timer
        )
        self.btn_timer_toggle.pack(side="left", expand=True, fill="x", padx=3)

        btn_timer_reset = tk.Button(
            action_frame,
            text="🔄 Đặt lại",
            font=("Segoe UI", 10, "bold"),
            bg="#475569",
            fg="#FFFFFF",
            relief="flat",
            padx=10,
            pady=8,
            cursor="hand2",
            command=self._reset_timer
        )
        btn_timer_reset.pack(side="left", expand=True, fill="x", padx=3)

        btn_add1m = tk.Button(
            action_frame,
            text="+1 Phút",
            font=("Segoe UI", 9, "bold"),
            bg="#334155",
            fg="#38BDF8",
            relief="flat",
            padx=8,
            pady=8,
            cursor="hand2",
            command=lambda: self.app.add_timer_seconds(60)
        )
        btn_add1m.pack(side="left", padx=3)

        self._update_timer_button_state()

    def _set_timer_preset(self, seconds):
        self.app.set_timer_seconds(seconds)
        self.app.switch_mode("timer")
        self.app.start_timer()
        self._update_timer_button_state()

    def _apply_custom_timer(self):
        try:
            h = int(self.spin_timer_h.get() or 0)
            m = int(self.spin_timer_m.get() or 0)
            s = int(self.spin_timer_s.get() or 0)
            total = h * 3600 + m * 60 + s
            if total <= 0:
                messagebox.showwarning("Lỗi", "Vui lòng nhập thời gian lớn hơn 0 giây!", parent=self)
                return
            self.app.set_timer_seconds(total)
            self.app.switch_mode("timer")
            self._update_timer_button_state()
        except ValueError:
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
            self.btn_timer_toggle.configure(text="▶ BẮT ĐẦU ĐẾM", bg="#10B981")

    # ---------------- ⏰ TAB ALARMS ----------------
    def _setup_alarm_tab(self):
        f = self.tab_alarm

        tk.Label(f, text="⏰ DANH SÁCH BÁO THỨC THÔNG MINH", font=("Segoe UI", 11, "bold"), bg="#151a24", fg="#EC4899").pack(anchor="w", pady=(0, 6))

        add_f = tk.Frame(f, bg="#1e2430", padx=10, pady=8, relief="groove", bd=1)
        add_f.pack(fill="x", pady=(0, 10))

        tk.Label(add_f, text="Thêm báo thức:", font=("Segoe UI", 9, "bold"), bg="#1e2430", fg="#cbd5e1").grid(row=0, column=0, padx=4)

        self.spin_alm_h = tk.Spinbox(add_f, from_=0, to=23, width=3, font=("Consolas", 11, "bold"), bg="#0f172a", fg="#EC4899", justify="center", buttonbackground="#334155")
        self.spin_alm_h.grid(row=0, column=1)
        self.spin_alm_h.delete(0, "end")
        self.spin_alm_h.insert(0, "07")

        tk.Label(add_f, text=":", bg="#1e2430", fg="#94a3b8", font=("Consolas", 11, "bold")).grid(row=0, column=2)

        self.spin_alm_m = tk.Spinbox(add_f, from_=0, to=59, width=3, font=("Consolas", 11, "bold"), bg="#0f172a", fg="#EC4899", justify="center", buttonbackground="#334155")
        self.spin_alm_m.grid(row=0, column=3)
        self.spin_alm_m.delete(0, "end")
        self.spin_alm_m.insert(0, "00")

        self.ent_alm_lbl = tk.Entry(add_f, font=("Segoe UI", 9), bg="#0f172a", fg="#ffffff", insertbackground="#ffffff", width=18)
        self.ent_alm_lbl.grid(row=0, column=4, padx=6)
        self.ent_alm_lbl.insert(0, "Báo thức mới")

        btn_add_alm = tk.Button(
            add_f,
            text="➕ Thêm",
            font=("Segoe UI", 9, "bold"),
            bg="#EC4899",
            fg="#FFFFFF",
            relief="flat",
            padx=10,
            pady=3,
            cursor="hand2",
            command=self._add_alarm
        )
        btn_add_alm.grid(row=0, column=5, padx=4)

        list_container = tk.Frame(f, bg="#151a24")
        list_container.pack(fill="both", expand=True)

        self.alarm_items_frame = tk.Frame(list_container, bg="#151a24")
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

        tk.Label(f, text="🍅 PHƯƠNG PHÁP QUẢN LÝ THỜI GIAN POMODORO", font=("Segoe UI", 11, "bold"), bg="#151a24", fg="#EF4444").pack(anchor="w", pady=(0, 4))
        tk.Label(f, text="Giúp tập trung làm việc hiệu quả và nghỉ ngơi khoa học theo chu kỳ.", font=("Segoe UI", 9), bg="#151a24", fg="#94a3b8").pack(anchor="w", pady=(0, 10))

        cfg_f = tk.Frame(f, bg="#1e2430", padx=12, pady=8, relief="groove", bd=1)
        cfg_f.pack(fill="x", pady=(0, 12))

        tk.Label(cfg_f, text="Tập trung (Work):", font=("Segoe UI", 9, "bold"), bg="#1e2430", fg="#fca5a5").grid(row=0, column=0, sticky="w", pady=3)
        self.spin_pomo_w = tk.Spinbox(cfg_f, from_=1, to=90, width=4, font=("Consolas", 10, "bold"), bg="#0f172a", fg="#EF4444", justify="center", buttonbackground="#334155")
        self.spin_pomo_w.grid(row=0, column=1, padx=6)
        self.spin_pomo_w.delete(0, "end")
        self.spin_pomo_w.insert(0, str(self.app.config.get("pomo_work_min", 25)))
        tk.Label(cfg_f, text="Phút", font=("Segoe UI", 9), bg="#1e2430", fg="#94a3b8").grid(row=0, column=2, sticky="w")

        tk.Label(cfg_f, text="Nghỉ ngắn (Break):", font=("Segoe UI", 9, "bold"), bg="#1e2430", fg="#86efac").grid(row=1, column=0, sticky="w", pady=3)
        self.spin_pomo_b = tk.Spinbox(cfg_f, from_=1, to=30, width=4, font=("Consolas", 10, "bold"), bg="#0f172a", fg="#10B981", justify="center", buttonbackground="#334155")
        self.spin_pomo_b.grid(row=1, column=1, padx=6)
        self.spin_pomo_b.delete(0, "end")
        self.spin_pomo_b.insert(0, str(self.app.config.get("pomo_break_min", 5)))
        tk.Label(cfg_f, text="Phút", font=("Segoe UI", 9), bg="#1e2430", fg="#94a3b8").grid(row=1, column=2, sticky="w")

        btn_apply_pomo = tk.Button(
            cfg_f,
            text="Lưu thiết lập",
            font=("Segoe UI", 9, "bold"),
            bg="#3b82f6",
            fg="#ffffff",
            relief="flat",
            padx=10,
            pady=3,
            cursor="hand2",
            command=self._apply_pomodoro_settings
        )
        btn_apply_pomo.grid(row=0, column=3, rowspan=2, padx=12)

        btn_start_pomo = tk.Button(
            f,
            text="🍅 BẮT ĐẦU CHU KỲ POMODORO",
            font=("Segoe UI", 11, "bold"),
            bg="#EF4444",
            fg="#FFFFFF",
            relief="flat",
            pady=8,
            cursor="hand2",
            command=self._start_pomodoro
        )
        btn_start_pomo.pack(fill="x", pady=4)

    def _apply_pomodoro_settings(self):
        try:
            w = int(self.spin_pomo_w.get())
            b = int(self.spin_pomo_b.get())
            self.app.config["pomo_work_min"] = w
            self.app.config["pomo_break_min"] = b
            self.app.save_config()
            messagebox.showinfo("Thành công", "Đã lưu thiết lập Pomodoro!", parent=self)
        except Exception:
            messagebox.showerror("Lỗi", "Thông số không hợp lệ!", parent=self)

    def _start_pomodoro(self):
        self._apply_pomodoro_settings()
        self.app.switch_mode("pomodoro")
        self.app.start_pomodoro_work()

    # ---------------- 🎨 TAB DISPLAY & AI GENZ ----------------
    def _setup_display_tab(self):
        f = self.tab_display

        # Mascot selector
        mascot_f = tk.Frame(f, bg="#151a24")
        mascot_f.pack(fill="x", pady=(0, 6))
        tk.Label(mascot_f, text="Linh vật / Avatar:", font=("Segoe UI", 9, "bold"), bg="#151a24", fg="#38bdf8").pack(side="left", padx=(0, 6))

        mascots = ["🚀", "☕", "🐱", "💎", "🔋", "🎯", "🔥", "⚡", "Ẩn"]
        for m in mascots:
            btn_m = tk.Button(
                mascot_f,
                text=m,
                font=("Segoe UI Emoji", 9, "bold"),
                bg="#1e293b",
                fg="#f8fafc",
                relief="flat",
                padx=6,
                pady=2,
                cursor="hand2",
                command=lambda mas=m: self._select_mascot(mas)
            )
            btn_m.pack(side="left", padx=2)

        # Color presets
        color_f = tk.Frame(f, bg="#151a24")
        color_f.pack(fill="x", pady=(0, 6))
        tk.Label(color_f, text="Màu chữ Neon:", font=("Segoe UI", 9, "bold"), bg="#151a24", fg="#e2e8f0").pack(side="left", padx=(0, 8))

        colors = [
            ("#00FFCC", "Cyan"),
            ("#10B981", "Lime"),
            ("#F59E0B", "Amber"),
            ("#EC4899", "Pink"),
            ("#38BDF8", "Sky"),
            ("#A855F7", "Violet"),
            ("#EF4444", "Red"),
            ("#FFFFFF", "White")
        ]
        for hex_col, name in colors:
            btn = tk.Button(
                color_f,
                bg=hex_col,
                width=2,
                height=1,
                relief="flat",
                cursor="hand2",
                command=lambda c=hex_col: self.app.set_text_color(c)
            )
            btn.pack(side="left", padx=2)

        btn_custom_col = tk.Button(
            color_f,
            text="Tùy chọn...",
            font=("Segoe UI", 8),
            bg="#334155",
            fg="#ffffff",
            relief="flat",
            padx=6,
            cursor="hand2",
            command=self.app.pick_custom_color
        )
        btn_custom_col.pack(side="left", padx=6)

        # AI Quotes API Configuration Box
        ai_box = tk.LabelFrame(f, text=" 🤖 CẤU HÌNH AI ĐỘNG VIÊN GENZ (GEMINI / OPENAI / GROQ) ", font=("Segoe UI", 9, "bold"), bg="#1e2430", fg="#FCD34D", padx=10, pady=6)
        ai_box.pack(fill="x", pady=(0, 8))

        ai_cfg = self.app.config.get("ai_quotes", {
            "enabled": True,
            "provider": "gemini",
            "api_key": "",
            "base_url": "https://api.openai.com/v1",
            "model": "gpt-4o-mini"
        })

        row_ai_1 = tk.Frame(ai_box, bg="#1e2430")
        row_ai_1.pack(fill="x", pady=2)

        tk.Label(row_ai_1, text="Nhà cung cấp AI:", font=("Segoe UI", 9), bg="#1e2430", fg="#cbd5e1").pack(side="left", padx=(0, 6))

        self.cmb_ai_provider = ttk.Combobox(row_ai_1, values=["Google Gemini (Miễn phí)", "Groq (Llama 3.3 - Siêu nhanh & Miễn phí)", "OpenAI (ChatGPT)", "Tùy chỉnh (OpenRouter / Custom)"], state="readonly", width=34)
        prov = ai_cfg.get("provider", "gemini")
        if prov == "gemini":
            self.cmb_ai_provider.current(0)
        elif prov == "groq":
            self.cmb_ai_provider.current(1)
        elif prov == "openai":
            self.cmb_ai_provider.current(2)
        else:
            self.cmb_ai_provider.current(3)
        self.cmb_ai_provider.pack(side="left", padx=(0, 10))

        row_ai_2 = tk.Frame(ai_box, bg="#1e2430")
        row_ai_2.pack(fill="x", pady=3)

        tk.Label(row_ai_2, text="API Key:", font=("Segoe UI", 9, "bold"), bg="#1e2430", fg="#FCD34D").pack(side="left", padx=(0, 6))
        self.ent_ai_key = tk.Entry(row_ai_2, font=("Consolas", 9), width=32, bg="#0f172a", fg="#ffffff", insertbackground="#fff")
        self.ent_ai_key.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.ent_ai_key.insert(0, ai_cfg.get("api_key", ""))

        btn_save_ai = tk.Button(
            row_ai_2,
            text="💾 Lưu Key",
            font=("Segoe UI", 9, "bold"),
            bg="#2563eb",
            fg="#ffffff",
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2",
            command=self._save_ai_config
        )
        btn_save_ai.pack(side="left", padx=2)

        btn_test_ai = tk.Button(
            row_ai_2,
            text="⚡ Test tạo câu AI",
            font=("Segoe UI", 9, "bold"),
            bg="#D97706",
            fg="#ffffff",
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2",
            command=self._test_ai_generation
        )
        btn_test_ai.pack(side="left", padx=2)

        self.lbl_ai_status = tk.Label(ai_box, text="💡 Gợi ý: Gắn API Key Gemini hoặc Groq (gsk_...) để AI sinh câu GenZ siêu tốc!", font=("Segoe UI", 8, "italic"), bg="#1e2430", fg="#94A3B8")
        self.lbl_ai_status.pack(anchor="w", pady=(2, 0))

        # Checkboxes
        opt_f = tk.Frame(f, bg="#1e2430", padx=10, pady=6, relief="groove", bd=1)
        opt_f.pack(fill="x", pady=(0, 6))

        self.var_mini_mode = tk.BooleanVar(value=self.app.config.get("mini_mode", False))
        chk_mini = tk.Checkbutton(
            opt_f,
            text="🔍 Chế độ THU NHỎ (Mini Mode - Chỉ hiện mỗi giờ số, ẩn mọi text phụ) [Phím M]",
            variable=self.var_mini_mode,
            font=("Segoe UI", 9, "bold"),
            bg="#1e2430",
            fg="#38BDF8",
            selectcolor="#0f172a",
            activebackground="#1e2430",
            activeforeground="#38BDF8",
            command=self._toggle_mini_mode_setting
        )
        chk_mini.pack(anchor="w", pady=1)

        self.var_dynamic_color = tk.BooleanVar(value=self.app.config.get("dynamic_time_color", True))
        chk_dynamic = tk.Checkbutton(
            opt_f,
            text="🌈 Tự động ĐỔI MÀU theo thời gian (>=8h: Đỏ • >=5h: Cam • >=2h: Vàng • >=1h: Xanh • <1h: Trắng) [Phím D]",
            variable=self.var_dynamic_color,
            font=("Segoe UI", 9, "bold"),
            bg="#1e2430",
            fg="#F43F5E",
            selectcolor="#0f172a",
            activebackground="#1e2430",
            activeforeground="#F43F5E",
            command=self._toggle_dynamic_color_setting
        )
        chk_dynamic.pack(anchor="w", pady=1)

        self.var_quote = tk.BooleanVar(value=self.app.config.get("show_quote", True))
        chk_quote = tk.Checkbutton(
            opt_f,
            text="💬 Hiển thị Câu nói khích lệ GenZ & Động lực làm việc",
            variable=self.var_quote,
            font=("Segoe UI", 9),
            bg="#1e2430",
            fg="#FCD34D",
            selectcolor="#0f172a",
            activebackground="#1e2430",
            activeforeground="#FCD34D",
            command=self._toggle_quote_setting
        )
        chk_quote.pack(anchor="w", pady=1)

        self.var_water = tk.BooleanVar(value=self.app.config.get("water_reminder", {}).get("enabled", True))
        chk_water = tk.Checkbutton(
            opt_f,
            text="💧 Bật nhắc nhở Uống nước & Vươn vai thư giãn (Mỗi 45 phút)",
            variable=self.var_water,
            font=("Segoe UI", 9),
            bg="#1e2430",
            fg="#38BDF8",
            selectcolor="#0f172a",
            activebackground="#1e2430",
            activeforeground="#38BDF8",
            command=self._toggle_water_setting
        )
        chk_water.pack(anchor="w", pady=1)

        self.var_progress = tk.BooleanVar(value=self.app.config.get("show_progress", True))
        chk_progress = tk.Checkbutton(
            opt_f,
            text="📊 Hiển thị % Tiến độ ngày làm việc hoàn thành",
            variable=self.var_progress,
            font=("Segoe UI", 9),
            bg="#1e2430",
            fg="#4ADE80",
            selectcolor="#0f172a",
            activebackground="#1e2430",
            activeforeground="#4ADE80",
            command=self._toggle_progress_setting
        )
        chk_progress.pack(anchor="w", pady=1)

        self.var_autostart = tk.BooleanVar(value=is_start_with_windows())
        chk_autostart = tk.Checkbutton(
            opt_f,
            text="🚀 Tự động khởi động cùng Windows (Start with Windows)",
            variable=self.var_autostart,
            font=("Segoe UI", 9, "bold"),
            bg="#1e2430",
            fg="#F59E0B",
            selectcolor="#0f172a",
            activebackground="#1e2430",
            activeforeground="#F59E0B",
            command=self._toggle_autostart_setting
        )
        chk_autostart.pack(anchor="w", pady=1)

        self.var_sys_monitor = tk.BooleanVar(value=self.app.config.get("show_sys_monitor", False))
        chk_sys = tk.Checkbutton(
            opt_f,
            text="📊 Giám sát CPU & RAM % theo thời gian thực (Win32 API)",
            variable=self.var_sys_monitor,
            font=("Segoe UI", 9),
            bg="#1e2430",
            fg="#A78BFA",
            selectcolor="#0f172a",
            activebackground="#1e2430",
            activeforeground="#A78BFA",
            command=self._toggle_sys_monitor_setting
        )
        chk_sys.pack(anchor="w", pady=1)

        self.var_autohide = tk.BooleanVar(value=self.app.config.get("auto_hide", False))
        chk_autohide = tk.Checkbutton(
            opt_f,
            text="🧲 Tự động làm mờ khi rời chuột (Auto-fade/hide) [Phím H]",
            variable=self.var_autohide,
            font=("Segoe UI", 9),
            bg="#1e2430",
            fg="#94A3B8",
            selectcolor="#0f172a",
            activebackground="#1e2430",
            activeforeground="#94A3B8",
            command=self._toggle_autohide_setting
        )
        chk_autohide.pack(anchor="w", pady=1)

        self.var_sound = tk.BooleanVar(value=self.app.config.get("sound_enabled", True))
        chk_sound = tk.Checkbutton(
            opt_f,
            text="🔊 Bật âm thanh chuông báo (Timer / Alarm / Pomodoro / Uống nước)",
            variable=self.var_sound,
            font=("Segoe UI", 9),
            bg="#1e2430",
            fg="#f8fafc",
            selectcolor="#0f172a",
            activebackground="#1e2430",
            activeforeground="#f8fafc",
            command=self._toggle_sound_setting
        )
        chk_sound.pack(anchor="w", pady=1)

    def _select_mascot(self, m):
        val = "" if m == "Ẩn" else m
        self.app.config["mascot"] = val
        self.app.save_config()

    def _save_ai_config(self):
        sel_idx = self.cmb_ai_provider.current()
        if sel_idx == 0:
            prov = "gemini"
        elif sel_idx == 1:
            prov = "groq"
        elif sel_idx == 2:
            prov = "openai"
        else:
            prov = "custom"
        key = self.ent_ai_key.get().strip()

        self.app.config.setdefault("ai_quotes", {})
        self.app.config["ai_quotes"]["provider"] = prov
        self.app.config["ai_quotes"]["api_key"] = key
        self.app.save_config()
        self.lbl_ai_status.configure(text=f"✅ Đã lưu cấu hình {prov.upper()} Key thành công!", fg="#4ADE80")
        messagebox.showinfo("Thành công", f"Đã lưu thiết lập API Key ({prov.upper()}) thành công!", parent=self)

    def _test_ai_generation(self):
        self._save_ai_config()
        self.lbl_ai_status.configure(text="⏳ AI đang sáng tạo câu nói GenZ, vui lòng chờ...", fg="#F59E0B")

        def _on_result(quote, is_ai, error):
            if is_ai and quote:
                self.lbl_ai_status.configure(text=f"✨ AI vừa tạo: \"{quote}\"", fg="#4ADE80")
                self.app.current_quote = quote
            else:
                msg = f"⚠️ Lỗi API: {error}" if error else f"✨ Đã đổi câu GenZ: \"{quote}\""
                self.lbl_ai_status.configure(text=msg[:70], fg="#FCD34D")
                self.app.current_quote = quote

        self.app.ai_mgr.fetch_ai_quote("afternoon", callback=_on_result)

    def _toggle_mini_mode_setting(self):
        val = self.var_mini_mode.get()
        self.app.config["mini_mode"] = val
        self.app.apply_mini_mode()
        self.app.save_config()

    def _toggle_dynamic_color_setting(self):
        val = self.var_dynamic_color.get()
        self.app.config["dynamic_time_color"] = val
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
        self.app.save_config()

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


# ==========================================
# 🌟 MAIN FLOATING CLOCK APPLICATION
# ==========================================
class FloatingClock:
    def __init__(self, root):
        self.root = root
        self.config = self.load_config()

        sound_mgr.sound_enabled = self.config.get("sound_enabled", True)
        self.ai_mgr = AIManager(self.config)
        self.weather_mgr = WeatherManager(self.config)
        self.focus_sound_mgr = FocusSoundManager(self.config)

        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", self.config["opacity"])

        self.bg_color = self.config["bg_color"]
        self.root.configure(bg=self.bg_color)

        self.drag_start_x = 0
        self.drag_start_y = 0

        self.current_mode = self.config.get("mode", "clock")

        # Timer state
        self.timer_duration = self.config.get("timer_duration", 300)
        self.timer_remaining = self.config.get("timer_remaining", self.timer_duration)
        self.timer_state = self.config.get("timer_state", "stopped")
        self.timer_last_tick = time.time()

        # Stopwatch state
        self.stopwatch_running = False
        self.stopwatch_start_time = 0
        self.stopwatch_elapsed = 0
        self.stopwatch_laps = []

        # Pomodoro state
        self.pomo_stage = "work"
        self.pomo_running = False
        self.pomo_remaining = self.config.get("pomo_work_min", 25) * 60
        self.pomo_cycle_count = 0

        # Alarms & Reminders state
        self.alert_dialog = None
        self.last_alarm_checked_min = -1
        self.last_water_remind_time = time.time()

        # Motivation Quote state
        self.current_quote = "🚀 Chúc fen một ngày làm việc siêu slay & năng suất!"
        self.last_quote_update_time = 0

        self.is_flashing = False
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

        self._build_ui()
        self.setup_bindings()
        self.create_context_menu()
        try:
            self.request_next_quote()
        except Exception:
            pass
        if self.config.get("weather", {}).get("enabled", True):
            try:
                self.refresh_weather()
            except Exception:
                pass
        self.adjust_size_and_position(initial=True)

        if self.config.get("click_through", False):
            self.apply_click_through(True)

        self.update_loop()

    def load_config(self):
        cfg = DEFAULT_CONFIG.copy()
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    cfg.update(data)
            except Exception:
                pass
        return cfg

    def save_config(self):
        try:
            self.config["x"] = self.root.winfo_x()
            self.config["y"] = self.root.winfo_y()
            self.config["mode"] = self.current_mode
            self.config["timer_duration"] = self.timer_duration
            self.config["timer_remaining"] = self.timer_remaining
            self.config["timer_state"] = self.timer_state
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception:
            pass

    def get_today_departure_info(self, now):
        work_cfg = self.config.get("work_departure", {
            "start_time": "08:30",
            "mon_fri_time": "17:45",
            "sat_time": "16:00",
            "auto_schedule": True
        })
        weekday = now.weekday()  # 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
        vn_days = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ Nhật"]
        tag = vn_days[weekday]
        if weekday == 5:
            # Saturday: 16:00
            dep_time = work_cfg.get("sat_time", "16:00") + ":00"
        elif weekday == 6:
            dep_time = work_cfg.get("mon_fri_time", "17:45") + ":00"
        else:
            # Mon - Fri: 17:45
            dep_time = work_cfg.get("mon_fri_time", "17:45") + ":00"
        return dep_time, tag

    def calculate_workday_progress(self, now):
        work_cfg = self.config.get("work_departure", {
            "start_time": "08:30",
            "mon_fri_time": "17:45",
            "sat_time": "16:00"
        })
        try:
            today_str = now.strftime("%Y-%m-%d")
            st_str = work_cfg.get("start_time", "08:30") + ":00"
            dep_time, _ = self.get_today_departure_info(now)

            dt_start = datetime.strptime(f"{today_str} {st_str}", "%Y-%m-%d %H:%M:%S")
            dt_end = datetime.strptime(f"{today_str} {dep_time}", "%Y-%m-%d %H:%M:%S")

            if now < dt_start:
                return 0
            elif now >= dt_end:
                return 100
            else:
                total_work_sec = (dt_end - dt_start).total_seconds()
                done_sec = (now - dt_start).total_seconds()
                return int((done_sec / total_work_sec) * 100)
        except Exception:
            return 0

    def get_current_context_tag(self):
        now = datetime.now()
        h = now.hour
        weekday = now.weekday()

        if weekday == 4 and h >= 14:
            return "friday"
        elif weekday == 5:
            return "saturday"
        elif h >= 16 and h < 18:
            return "leaving_soon"
        elif h >= 18:
            return "night"
        elif h >= 11 and h < 13:
            return "lunch"
        elif h >= 6 and h < 11:
            return "morning"
        else:
            return "afternoon"

    def request_next_quote(self):
        ctx = self.get_current_context_tag()

        def _on_quote_received(quote, is_ai, error):
            if quote:
                self.current_quote = quote
                self.last_quote_update_time = time.time()
                if self.config.get("show_quote", True):
                    self.quote_label.configure(text=quote)
                self._check_and_resize(self.time_label.cget("text"), self.sub_label.cget("text"))

        self.ai_mgr.fetch_ai_quote(ctx, callback=_on_quote_received)

    def get_dynamic_color_by_seconds(self, remaining_sec, is_elapsed=False):
        """
        Tự động đổi màu theo mốc thời gian:
        - >= 8 tiếng: Đỏ (#EF4444)
        - >= 5 tiếng: Cam (#F97316)
        - >= 2 tiếng: Vàng (#FBBF24)
        - >= 1 tiếng: Xanh lá (#10B981)
        - < 1 tiếng: Trắng sáng (#FFFFFF)
        """
        if not self.config.get("dynamic_time_color", True):
            return self.config.get("text_color", "#00FFCC")

        hrs = max(0.0, float(remaining_sec) / 3600.0)
        if hrs >= 8.0:
            return "#EF4444"  # Đỏ (>= 8 tiếng)
        elif hrs >= 5.0:
            return "#F97316"  # Cam (>= 5 tiếng)
        elif hrs >= 2.0:
            return "#FBBF24"  # Vàng (>= 2 tiếng)
        elif hrs >= 1.0:
            return "#10B981"  # Xanh lá (>= 1 tiếng)
        else:
            return "#FFFFFF"  # Trắng sáng (< 1 tiếng)

    def calculate_salary_today(self, now):
        info = self.calculate_salary_info(now)
        return info["daily_earned"], info["daily_str"]

    def calculate_salary_info(self, now):
        sal_cfg = self.config.get("salary", {})
        if not sal_cfg.get("enabled", False):
            return {"daily_earned": 0.0, "month_earned": 0.0, "daily_str": "", "month_str": "", "show_daily": False, "show_monthly": False}

        monthly = float(sal_cfg.get("monthly", 15000000))
        work_days = max(1, sal_cfg.get("work_days", 22))
        work_hours = max(1.0, float(sal_cfg.get("work_hours", 8.0)))

        # Phân rã lương: 1 Ngày -> 1 Giờ -> 1 Giây
        daily_rate = monthly / work_days
        hourly_rate = daily_rate / work_hours
        sec_rate = hourly_rate / 3600.0

        work_cfg = self.config.get("work_departure", {
            "start_time": "08:30",
            "mon_fri_time": "17:45",
            "sat_time": "16:00",
            "lunch_start": "12:00",
            "lunch_end": "13:15"
        })
        today_str = now.strftime("%Y-%m-%d")
        st_str = work_cfg.get("start_time", "08:30") + ":00"
        dep_time, _ = self.get_today_departure_info(now)
        ls_str = work_cfg.get("lunch_start", "12:00") + ":00"
        le_str = work_cfg.get("lunch_end", "13:15") + ":00"

        daily_earned = 0.0
        worked_hours = 0.0
        is_lunch = False

        try:
            dt_start = datetime.strptime(f"{today_str} {st_str}", "%Y-%m-%d %H:%M:%S")
            dt_end = datetime.strptime(f"{today_str} {dep_time}", "%Y-%m-%d %H:%M:%S")
            dt_lunch_start = datetime.strptime(f"{today_str} {ls_str}", "%Y-%m-%d %H:%M:%S")
            dt_lunch_end = datetime.strptime(f"{today_str} {le_str}", "%Y-%m-%d %H:%M:%S")

            if now <= dt_start:
                daily_earned = 0.0
                worked_hours = 0.0
            elif now >= dt_end:
                worked_hours = work_hours
                daily_earned = daily_rate
            else:
                if dt_start < dt_lunch_start < dt_lunch_end < dt_end:
                    if now < dt_lunch_start:
                        worked_sec = (now - dt_start).total_seconds()
                    elif dt_lunch_start <= now < dt_lunch_end:
                        is_lunch = True
                        worked_sec = (dt_lunch_start - dt_start).total_seconds()
                    else:
                        morning_sec = (dt_lunch_start - dt_start).total_seconds()
                        afternoon_sec = (now - dt_lunch_end).total_seconds()
                        worked_sec = morning_sec + afternoon_sec
                else:
                    total_window_sec = (dt_end - dt_start).total_seconds()
                    ratio = (now - dt_start).total_seconds() / max(1.0, total_window_sec)
                    worked_sec = ratio * (work_hours * 3600.0)

                worked_sec = max(0.0, min(work_hours * 3600.0, worked_sec))
                worked_hours = worked_sec / 3600.0
                # Tiền lương = Số giờ đã làm việc * Lương theo giờ
                daily_earned = worked_hours * hourly_rate
        except Exception:
            daily_earned = 0.0
            worked_hours = 0.0

        # Calculate month accumulation up to yesterday based on calc_cycle
        cycle_mode = sal_cfg.get("calc_cycle", "calendar_month")
        payday_day = self.config.get("payday_day", 5)
        past_work_days = 0
        cycle_label = f"Tháng {now.month}"

        if cycle_mode == "payday_cycle":
            try:
                if now.day >= payday_day:
                    dt_c_start = datetime(now.year, now.month, min(28, payday_day)).date()
                else:
                    if now.month == 1:
                        dt_c_start = datetime(now.year - 1, 12, min(28, payday_day)).date()
                    else:
                        dt_c_start = datetime(now.year, now.month - 1, min(28, payday_day)).date()

                cur_d = dt_c_start
                yesterday = now.date() - timedelta(days=1)
                while cur_d <= yesterday:
                    w_day = cur_d.weekday()
                    if work_days >= 24:
                        if w_day <= 5:
                            past_work_days += 1
                    else:
                        if w_day <= 4:
                            past_work_days += 1
                    cur_d += timedelta(days=1)
                cycle_label = f"Kỳ {dt_c_start.strftime('%d/%m')}"
            except Exception:
                cycle_label = f"Kỳ Lương"
        else:
            cur_year = now.year
            cur_month = now.month
            for day in range(1, now.day):
                try:
                    dt_d = datetime(cur_year, cur_month, day)
                    w_day = dt_d.weekday()
                    if work_days >= 24:
                        if w_day <= 5:
                            past_work_days += 1
                    else:
                        if w_day <= 4:
                            past_work_days += 1
                except Exception:
                    pass
            cycle_label = f"Tháng {now.month}"

        month_earned = min(monthly, (past_work_days * daily_rate) + daily_earned)
        pct_month = (month_earned / monthly) * 100.0 if monthly > 0 else 0.0

        is_weekend = (now.weekday() == 6) or (now.weekday() == 5 and work_days <= 22)
        is_hidden = sal_cfg.get("hidden", False)

        if is_hidden:
            daily_str = "💸 Ngày: •••••• đ"
            month_str = f"📅 {cycle_label}: •••••• đ"
        elif is_weekend:
            daily_str = "💸 Ngày: Nghỉ cuối tuần 🌴"
            month_str = f"📅 {cycle_label}: {int(month_earned):,} đ ({pct_month:.1f}%)".replace(",", ".")
        elif now < dt_start:
            daily_str = f"💸 Ngày: Chuẩn bị vào ca ☕ ({int(hourly_rate):,}đ/h)".replace(",", ".")
            month_str = f"📅 {cycle_label}: {int(month_earned):,} đ ({pct_month:.1f}%)".replace(",", ".")
        elif now >= dt_end:
            daily_str = f"💸 Ngày: +{int(daily_earned):,} đ (Xong ca 🎉)".replace(",", ".")
            month_str = f"📅 {cycle_label}: {int(month_earned):,} đ ({pct_month:.1f}%)".replace(",", ".")
        elif is_lunch:
            daily_str = f"💸 Ngày: +{int(daily_earned):,} đ (Nghỉ trưa 🍱)".replace(",", ".")
            month_str = f"📅 {cycle_label}: {int(month_earned):,} đ ({pct_month:.1f}%)".replace(",", ".")
        else:
            daily_str = f"💸 Ngày: +{int(daily_earned):,} đ".replace(",", ".")
            month_str = f"📅 {cycle_label}: {int(month_earned):,} đ ({pct_month:.1f}%)".replace(",", ".")

        return {
            "daily_earned": daily_earned,
            "month_earned": month_earned,
            "daily_str": daily_str,
            "month_str": month_str,
            "show_daily": sal_cfg.get("show_daily", True),
            "show_monthly": sal_cfg.get("show_monthly", True)
        }

    def get_payday_countdown_info(self, now, payday_day=5):
        year = now.year
        month = now.month
        try:
            target_payday = datetime(year, month, payday_day, 9, 0, 0)
            if now > target_payday:
                if month == 12:
                    target_payday = datetime(year + 1, 1, payday_day, 9, 0, 0)
                else:
                    target_payday = datetime(year, month + 1, payday_day, 9, 0, 0)
            diff_days = (target_payday - now).total_seconds() / 86400.0
            days_int = int(math.ceil(diff_days))
            return days_int, target_payday.strftime("%d/%m/%Y")
        except Exception:
            return 0, ""

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
        self.adjust_size_and_position(initial=False)

    def _build_ui(self):
        is_mini = self.config.get("mini_mode", False)
        pad_x = 10 if is_mini else 16
        pad_y = 2 if is_mini else 4

        self.frame = tk.Frame(
            self.root,
            bg=self.bg_color,
            highlightthickness=1,
            highlightbackground=self.config.get("border_color", "#2a3447"),
            padx=pad_x,
            pady=pad_y
        )
        self.frame.pack(fill="both", expand=True)

        self.sub_label = tk.Label(
            self.frame,
            text="🚀 🕒 CLOCK",
            font=("Segoe UI", 8, "bold"),
            fg="#94A3B8",
            bg=self.bg_color
        )

        self.time_label = tk.Label(
            self.frame,
            text="00:00:00",
            font=("Consolas", self.config["font_size"], "bold"),
            fg=self.config["text_color"],
            bg=self.bg_color
        )

        self.date_label = tk.Label(
            self.frame,
            text="",
            font=("Segoe UI", 8),
            fg="#64748B",
            bg=self.bg_color
        )

        # 💸 Dòng 1: Lương Ngày (Hôm nay)
        self.salary_daily_label = tk.Label(
            self.frame,
            text="",
            font=("Segoe UI", 8, "bold"),
            fg="#34D399",
            bg=self.bg_color,
            cursor="hand2"
        )
        self.salary_daily_label.bind("<ButtonRelease-1>", lambda e: self.toggle_salary_hide())

        # 📅 Dòng 2: Lương Tháng (Tích lũy)
        self.salary_month_label = tk.Label(
            self.frame,
            text="",
            font=("Segoe UI", 8, "bold"),
            fg="#6EE7B7",
            bg=self.bg_color,
            cursor="hand2"
        )
        self.salary_month_label.bind("<ButtonRelease-1>", lambda e: self.toggle_salary_hide())

        # 🎯 Task Trọng Tâm (Focus MIT)
        self.task_label = tk.Label(
            self.frame,
            text="",
            font=("Segoe UI", 8, "bold"),
            fg="#FCD34D",
            bg=self.bg_color,
            cursor="hand2"
        )
        self.task_label.bind("<ButtonRelease-1>", lambda e: self.open_quick_task_dialog())

        # 🌦️ Dự báo thời tiết (Open-Meteo)
        self.weather_label = tk.Label(
            self.frame,
            text="",
            font=("Segoe UI", 8),
            fg="#38BDF8",
            bg=self.bg_color,
            cursor="hand2"
        )
        self.weather_label.bind("<ButtonRelease-1>", lambda e: WeatherForecastDialog(self))

        # 🎧 Âm thanh tập trung (White Noise status)
        self.sound_status_label = tk.Label(
            self.frame,
            text="",
            font=("Segoe UI", 8),
            fg="#A78BFA",
            bg=self.bg_color,
            cursor="hand2"
        )
        self.sound_status_label.bind("<ButtonRelease-1>", lambda e: self.toggle_focus_sound())

        self.quote_label = tk.Label(
            self.frame,
            text=self.current_quote,
            font=("Segoe UI", 8, "italic"),
            fg="#FCD34D",
            bg=self.bg_color,
            cursor="hand2"
        )

        self.sys_info_label = tk.Label(
            self.frame,
            text="",
            font=("Consolas", 7),
            fg="#94A3B8",
            bg=self.bg_color
        )

        if not is_mini:
            if self.config.get("show_sublabel", True):
                self.sub_label.pack(anchor="center", pady=(0, 1))
            self.time_label.pack(anchor="center")
            if self.config.get("show_date", True) and self.current_mode == "clock":
                self.date_label.pack(anchor="center", pady=(1, 0))
            self.update_extra_info_visibility()
            if self.config.get("show_quote", True):
                self.quote_label.pack(anchor="center", pady=(2, 0))
        else:
            self.time_label.pack(anchor="center")

    def update_date_visibility(self):
        if not self.config.get("mini_mode", False) and self.config.get("show_date", True) and self.current_mode == "clock":
            self.date_label.pack(anchor="center", pady=(1, 0))
        else:
            self.date_label.pack_forget()
        self.adjust_size_and_position(initial=False)

    def update_quote_visibility(self):
        if not self.config.get("mini_mode", False) and self.config.get("show_quote", True):
            self.quote_label.pack(anchor="center", pady=(2, 0))
        else:
            self.quote_label.pack_forget()
        self.adjust_size_and_position(initial=False)

    def update_sublabel_visibility(self):
        if not self.config.get("mini_mode", False) and self.config.get("show_sublabel", True):
            self.sub_label.pack(anchor="center", pady=(0, 1), before=self.time_label)
        else:
            self.sub_label.pack_forget()
        self.adjust_size_and_position(initial=False)

    def toggle_focus_sound(self, sound_type=None):
        st = sound_type or self.config.get("focus_sound", {}).get("sound_type", "rain")
        self.focus_sound_mgr.toggle(st)
        self.update_extra_info_visibility()

    def select_and_play_sound(self, sound_type):
        self.config.setdefault("focus_sound", {})["sound_type"] = sound_type
        self.config["focus_sound"]["enabled"] = True
        self.save_config()
        self.focus_sound_mgr.play(sound_type)
        self.update_extra_info_visibility()

    def refresh_weather(self):
        def _on_weather(txt, data):
            self.update_extra_info_visibility()
        self.weather_mgr.fetch_weather(callback=_on_weather)

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
            self.salary_daily_label.pack(anchor="center", pady=(1, 0))
        else:
            self.salary_daily_label.pack_forget()

        if sal_on and sal_cfg.get("show_monthly", True):
            self.salary_month_label.pack(anchor="center", pady=(1, 0))
        else:
            self.salary_month_label.pack_forget()

        task_on = self.config.get("focus_task", {}).get("enabled", False)
        if task_on:
            self.task_label.pack(anchor="center", pady=(1, 0))
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
            s_icon = snd_info.get("icon", "🎧")
            s_name = snd_info.get("name", "Âm thanh")
            self.sound_status_label.configure(text=f"{s_icon} Đang phát: {s_name} [F9 tắt]")
            self.sound_status_label.pack(anchor="center", pady=(1, 0))
        else:
            self.sound_status_label.pack_forget()

        self.adjust_size_and_position(initial=False)

    def setup_bindings(self):
        for widget in (self.root, self.frame, self.time_label, self.sub_label, self.date_label, self.quote_label, self.salary_daily_label, self.salary_month_label, self.task_label, self.sys_info_label, self.weather_label, self.sound_status_label):
            widget.bind("<ButtonPress-1>", self.start_drag)
            widget.bind("<B1-Motion>", self.do_drag)
            widget.bind("<ButtonRelease-1>", self.stop_drag)
            widget.bind("<Button-3>", self.show_context_menu)
            widget.bind("<Double-Button-1>", self.on_double_click)

        # Clicking quote changes / fetches next quote
        self.quote_label.bind("<ButtonRelease-1>", lambda e: self.request_next_quote())

        # Auto-hide bindings
        self.root.bind("<Enter>", self.on_mouse_enter)
        self.root.bind("<Leave>", self.on_mouse_leave)

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

    def start_drag(self, event):
        if not self.config["locked"]:
            self.drag_start_x = event.x_root - self.root.winfo_x()
            self.drag_start_y = event.y_root - self.root.winfo_y()

    def do_drag(self, event):
        if not self.config["locked"]:
            x = event.x_root - self.drag_start_x
            y = event.y_root - self.drag_start_y
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            w = max(50, self.root.winfo_width())
            h = max(20, self.root.winfo_height())
            x = max(0, min(sw - w, x))
            y = max(0, min(sh - h, y))
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

    # ---------------- 🎛️ CONTEXT MENU ----------------
    def create_context_menu(self):
        menu_bg = "#151a24"
        menu_fg = "#f1f5f9"
        active_bg = "#2563eb"
        active_fg = "#ffffff"
        menu_font = ("Segoe UI", 9)

        self.menu = tk.Menu(
            self.root,
            tearoff=0,
            bg=menu_bg,
            fg=menu_fg,
            activebackground=active_bg,
            activeforeground=active_fg,
            font=menu_font
        )

        # 1. ⚙️ BẢNG ĐIỀU KHIỂN & CÀI ĐẶT TOÀN DIỆN (Nổi bật đầu tiên)
        self.menu.add_command(
            label="⚙️  Bảng điều khiển & Cài đặt...",
            font=("Segoe UI", 9, "bold"),
            command=self.open_control_center
        )
        self.menu.add_separator()

        # 2. 🌟 TIỆN ÍCH & THÔNG TIN HÔM NAY (WIDGETS & REALTIME)
        now = datetime.now()
        today_dep, today_tag = self.get_today_departure_info(now)
        self.menu.add_command(
            label=f"🏢  Đếm ngược tan làm ({today_tag}: {today_dep[:5]})",
            command=self.activate_today_departure
        )

        p_days, p_date = self.get_payday_countdown_info(now, self.config.get("payday_day", 5))
        self.menu.add_command(
            label=f"💸  Lương Ting Ting: Còn {p_days} ngày ({p_date})",
            command=self.open_control_center
        )

        self.menu.add_command(
            label="🎯  Task trọng tâm hôm nay... [T]",
            command=self.open_quick_task_dialog
        )

        w_data = self.weather_mgr.current_data
        w_city = self.config.get("weather", {}).get("city_name", "")
        if w_data and "temp" in w_data:
            w_icon = w_data.get("icon", "🌤️")
            w_temp = w_data.get("temp", "")
            w_desc = w_data.get("desc", "")
            w_label = f"{w_icon}  Thời tiết: {w_city} ({w_temp}°C • {w_desc}) [W]"
        elif self.weather_mgr.current_weather_str:
            w_label = f"🌦️  {self.weather_mgr.current_weather_str} [W]"
        else:
            w_label = "🌦️  Xem dự báo thời tiết... [W]"

        self.menu.add_command(
            label=w_label,
            command=lambda: WeatherForecastDialog(self)
        )

        # Focus sound submenu
        focus_menu = tk.Menu(self.menu, tearoff=0, bg=menu_bg, fg=menu_fg, activebackground=active_bg, activeforeground=active_fg, font=menu_font)
        is_snd_playing = self.focus_sound_mgr.is_playing
        cur_snd = self.config.get("focus_sound", {}).get("sound_type", "rain")

        for s_key, s_data in self.focus_sound_mgr.SOUND_TYPES.items():
            pfx = "✓ " if (is_snd_playing and cur_snd == s_key) else "   "
            focus_menu.add_command(
                label=f"{pfx}{s_data['icon']} {s_data['name']}",
                command=lambda k=s_key: self.select_and_play_sound(k)
            )
        focus_menu.add_separator()
        if is_snd_playing:
            focus_menu.add_command(label="⏹ Tắt âm thanh tập trung [F9]", command=lambda: self.toggle_focus_sound())
        else:
            focus_menu.add_command(label="▶ Bật âm thanh tập trung [F9]", command=lambda: self.toggle_focus_sound())

        self.menu.add_cascade(
            label=f"{'✓ ' if is_snd_playing else '   '}🎧  Âm thanh tập trung (White Noise) [F9]",
            menu=focus_menu
        )

        self.menu.add_command(
            label="💬  Đổi câu động viên GenZ mới 🎲",
            command=self.request_next_quote
        )
        self.menu.add_separator()

        # 3. 🔄 CHẾ ĐỘ & BỘ ĐẾM GIỜ (MODES & TIMERS)
        mode_menu = tk.Menu(self.menu, tearoff=0, bg=menu_bg, fg=menu_fg, activebackground=active_bg, activeforeground=active_fg, font=menu_font)
        modes = [
            ("🕒 Đồng hồ thời gian thực", "clock"),
            ("🎯 Đến thời gian / Tan làm", "target_time"),
            ("⏳ Đếm ngược (Countdown Timer)", "timer"),
            ("⏱️ Bấm giờ thể thao (Stopwatch)", "stopwatch"),
            ("🍅 Pomodoro (Làm việc tập trung)", "pomodoro"),
        ]
        for label, m in modes:
            prefix = "✓ " if self.current_mode == m else "   "
            mode_menu.add_command(label=f"{prefix}{label}", command=lambda mode_name=m: self.switch_mode(mode_name))
        self.menu.add_cascade(label="🔄  Chế độ hoạt động [F2]", menu=mode_menu)

        timer_sub = tk.Menu(self.menu, tearoff=0, bg=menu_bg, fg=menu_fg, activebackground=active_bg, activeforeground=active_fg, font=menu_font)
        for name, sec in [("1 Phút", 60), ("3 Phút", 180), ("5 Phút", 300), ("10 Phút", 600), ("15 Phút", 900), ("25 Phút", 1500), ("30 Phút", 1800), ("1 Giờ", 3600)]:
            timer_sub.add_command(label=name, command=lambda s=sec: self.start_quick_timer(s))
        self.menu.add_cascade(label="⏳  Đặt nhanh đếm ngược", menu=timer_sub)
        self.menu.add_separator()

        # 4. ⚡ BẬT / TẮT NHANH (QUICK TOGGLES)
        is_mini = self.config.get("mini_mode", False)
        self.menu.add_command(
            label=f"{'✓ ' if is_mini else '   '}🔍  Chế độ thu nhỏ tối giản [M]",
            command=self.toggle_mini_mode
        )

        is_dyn = self.config.get("dynamic_time_color", True)
        self.menu.add_command(
            label=f"{'✓ ' if is_dyn else '   '}🌈  Đổi màu động theo thời gian [D]",
            command=self.toggle_dynamic_color
        )

        is_hid_sal = self.config.get("salary", {}).get("hidden", False)
        self.menu.add_command(
            label=f"{'✓ ' if is_hid_sal else '   '}🔒  Ẩn / Che số tiền lương [S]",
            command=self.toggle_salary_hide
        )

        is_autohide = self.config.get("auto_hide", False)
        self.menu.add_command(
            label=f"{'✓ ' if is_autohide else '   '}🧲  Tự làm mờ khi rời chuột [H]",
            command=self.toggle_autohide
        )
        self.menu.add_separator()

        # 5. 🎨 GIAO DIỆN & VỊ TRÍ (APPEARANCE & POSITION)
        color_menu = tk.Menu(self.menu, tearoff=0, bg=menu_bg, fg=menu_fg, activebackground=active_bg, activeforeground=active_fg, font=menu_font)
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
            pfx = "✓ " if self.config.get("text_color") == col else "   "
            color_menu.add_command(label=f"{pfx}{name}", command=lambda c=col: self.set_text_color(c))
        color_menu.add_separator()
        color_menu.add_command(label="🎨 Màu tùy chọn...", command=self.pick_custom_color)
        self.menu.add_cascade(label="🎨  Đổi màu chữ cố định", menu=color_menu)

        opacity_menu = tk.Menu(self.menu, tearoff=0, bg=menu_bg, fg=menu_fg, activebackground=active_bg, activeforeground=active_fg, font=menu_font)
        for val in [1.0, 0.9, 0.75, 0.6, 0.4]:
            pfx = "✓ " if abs(self.config.get("opacity", 0.9) - val) < 0.05 else "   "
            opacity_menu.add_command(label=f"{pfx}{int(val * 100)}%", command=lambda v=val: self.set_opacity(v))
        self.menu.add_cascade(label="🌫️  Độ trong suốt (Opacity)", menu=opacity_menu)

        size_menu = tk.Menu(self.menu, tearoff=0, bg=menu_bg, fg=menu_fg, activebackground=active_bg, activeforeground=active_fg, font=menu_font)
        for sz in [14, 16, 18, 20, 24, 28, 32, 38]:
            pfx = "✓ " if self.config.get("font_size") == sz else "   "
            size_menu.add_command(label=f"{pfx}Cỡ {sz}px", command=lambda s=sz: self.set_font_size(s))
        self.menu.add_cascade(label="🔤  Kích thước chữ", menu=size_menu)

        pos_menu = tk.Menu(self.menu, tearoff=0, bg=menu_bg, fg=menu_fg, activebackground=active_bg, activeforeground=active_fg, font=menu_font)
        pos_menu.add_command(label="Đỉnh giữa (Top Center)", command=self.reset_to_top_center)
        pos_menu.add_command(label="Đỉnh phải (Top Right)", command=self.reset_to_top_right)
        pos_menu.add_command(label="Đỉnh trái (Top Left)", command=self.reset_to_top_left)
        pos_menu.add_command(label="Đáy giữa (Bottom Center)", command=self.reset_to_bottom_center)
        self.menu.add_cascade(label="📍  Căn vị trí nhanh", menu=pos_menu)
        self.menu.add_separator()

        # 6. 💻 HỆ THỐNG & CỬA SỔ (SYSTEM & WINDOW)
        is_autostart = is_start_with_windows()
        self.menu.add_command(
            label=f"{'✓ ' if is_autostart else '   '}🚀  Khởi động cùng Windows",
            command=lambda: set_start_with_windows(not is_autostart)
        )

        self.menu.add_command(
            label=f"{'✓ ' if self.config['locked'] else '   '}🔒  Khóa vị trí (Chống kéo nhầm)",
            command=self.toggle_lock
        )

        self.menu.add_command(
            label=f"{'✓ ' if self.config['click_through'] else '   '}🖱️  Xuyên chuột [F8]",
            command=self.toggle_click_through
        )
        self.menu.add_separator()

        # 7. ❌ ĐÓNG ỨNG DỤNG
        self.menu.add_command(
            label="❌  Đóng ứng dụng",
            font=("Segoe UI", 9, "bold"),
            command=self.quit_app
        )

    def show_context_menu(self, event):
        self.create_context_menu()
        self.menu.tk_popup(event.x_root, event.y_root)

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

    # ---------------- 🔄 MODE SWITCHING ----------------
    def switch_mode(self, mode_name):
        self.current_mode = mode_name
        self.config["mode"] = mode_name

        if mode_name == "clock":
            self.update_date_visibility()
        else:
            self.update_date_visibility()

        self.save_config()
        self.adjust_size_and_position(initial=False)

    def cycle_next_mode(self):
        modes = ["clock", "target_time", "timer", "stopwatch", "pomodoro"]
        try:
            curr_idx = modes.index(self.current_mode)
            next_idx = (curr_idx + 1) % len(modes)
        except ValueError:
            next_idx = 0
        self.switch_mode(modes[next_idx])

    # ---------------- ⏳ TIMER LOGIC ----------------
    def start_quick_timer(self, seconds):
        self.set_timer_seconds(seconds)
        self.switch_mode("timer")
        self.start_timer()

    def set_timer_seconds(self, seconds):
        self.timer_duration = seconds
        self.timer_remaining = seconds
        self.timer_state = "stopped"
        self.save_config()

    def add_timer_seconds(self, seconds):
        self.timer_remaining += seconds
        self.timer_duration += seconds
        self.save_config()

    def start_timer(self):
        if self.timer_remaining <= 0:
            self.timer_remaining = self.timer_duration
        self.timer_state = "running"
        self.timer_last_tick = time.time()
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
        self.stopwatch_elapsed = 0
        self.stopwatch_laps = []

    def lap_stopwatch(self):
        if not self.stopwatch_running:
            return
        curr_total = time.time() - self.stopwatch_start_time
        prev_total = self.stopwatch_laps[-1]["total_sec"] if self.stopwatch_laps else 0
        lap_sec = curr_total - prev_total

        total_str = self._format_stopwatch_str(curr_total)
        lap_str = self._format_stopwatch_str(lap_sec)

        self.stopwatch_laps.append({
            "total_sec": curr_total,
            "lap_sec": lap_sec,
            "total_str": total_str,
            "lap_str": lap_str
        })

    def _format_stopwatch_str(self, seconds):
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        cs = int((seconds * 100) % 100)
        if mins >= 60:
            hrs = mins // 60
            mins = mins % 60
            return f"{hrs:02d}:{mins:02d}:{secs:02d}.{cs:02d}"
        return f"{mins:02d}:{secs:02d}.{cs:02d}"

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

            self.check_alarms(now)
            self.check_target_time(now)
            self.check_water_reminder()

            # Rotate quote automatically every 45 seconds
            if time.time() - self.last_quote_update_time > 45:
                self.request_next_quote()

            # Check weather update (every 30m by default)
            w_cfg = self.config.get("weather", {})
            if w_cfg.get("enabled", True):
                w_interval = max(5, w_cfg.get("auto_refresh_min", 30)) * 60
                if time.time() - getattr(self, "_last_weather_check", 0) > w_interval:
                    self._last_weather_check = time.time()
                    self.refresh_weather()

            # Render extra info (Salary ticker 2 dòng: Ngày & Tháng + Focus MIT Task)
            if not self.config.get("mini_mode", False):
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
                    cur_sec = int(time.time())
                    if cur_sec != getattr(self, "_last_sys_check_sec", 0):
                        self._last_sys_check_sec = cur_sec
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
        if self.config.get("time_format_12h", False):
            time_str = now.strftime("%I:%M:%S %p")
        elif self.config.get("show_ms", False):
            time_str = now.strftime("%H:%M:%S") + f".{now.microsecond // 100000}"
        else:
            time_str = now.strftime("%H:%M:%S")

        # Color based on remaining workday time if dynamic color is enabled
        if self.config.get("dynamic_time_color", True):
            try:
                dep_str, _ = self.get_today_departure_info(now)
                today_str = now.strftime("%Y-%m-%d")
                dep_dt = datetime.strptime(f"{today_str} {dep_str}", "%Y-%m-%d %H:%M:%S")
                diff_work = (dep_dt - now).total_seconds()
                if 0 <= diff_work <= 16 * 3600:
                    fg_col = self.get_dynamic_color_by_seconds(diff_work)
                else:
                    fg_col = self.config.get("text_color", "#00FFCC")
            except Exception:
                fg_col = self.config.get("text_color", "#00FFCC")
        else:
            fg_col = self.config.get("text_color", "#00FFCC")

        self.time_label.configure(text=time_str, fg=fg_col)

        active_alarms = [a for a in self.config.get("alarms", []) if a.get("enabled", False)]
        if active_alarms:
            next_alm = sorted(active_alarms, key=lambda x: x["time"])[0]
            sub_txt = f"{mascot_prefix}🕒 CLOCK  •  ⏰ {next_alm['time']}"
        else:
            sub_txt = f"{mascot_prefix}🕒 CLOCK"

        self.sub_label.configure(text=sub_txt, fg="#94A3B8")

        vn_days = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
        day_str = f"{vn_days[now.weekday()]}, {now.strftime('%d/%m/%Y')}"

        if self.config.get("show_progress", True):
            pct = self.calculate_workday_progress(now)
            day_str += f"  •  📊 {pct}% Ngày"

        self.date_label.configure(text=day_str)
        self._check_and_resize(time_str, sub_txt)

    def _render_timer_mode(self, mascot_prefix):
        if self.timer_state == "running":
            cur_time = time.time()
            elapsed = cur_time - self.timer_last_tick
            self.timer_last_tick = cur_time
            self.timer_remaining -= elapsed

            if self.timer_remaining <= 0:
                self.timer_remaining = 0
                self.trigger_timer_finished()

        rem_sec = max(0, int(math.ceil(self.timer_remaining)))
        h = rem_sec // 3600
        m = (rem_sec % 3600) // 60
        s = rem_sec % 60

        if h > 0:
            time_str = f"{h:02d}:{m:02d}:{s:02d}"
        else:
            time_str = f"{m:02d}:{s:02d}"

        if self.timer_state == "paused":
            fg_col = "#F59E0B"
        elif self.config.get("dynamic_time_color", True):
            fg_col = self.get_dynamic_color_by_seconds(rem_sec)
        else:
            fg_col = self.config.get("text_color", "#00FFCC")

        state_tag = "▶ ĐANG ĐẾM" if self.timer_state == "running" else ("⏸ TẠM DỪNG" if self.timer_state == "paused" else "⏹ ĐÃ DỪNG")
        sub_txt = f"{mascot_prefix}⏳ TIMER • {state_tag}"

        self.sub_label.configure(text=sub_txt, fg="#38BDF8")
        self.time_label.configure(text=time_str, fg=fg_col)
        self._check_and_resize(time_str, sub_txt)

    def _render_target_time_mode(self, now, mascot_prefix):
        tgt_str = self.config.get("target_time_str", "17:45:00")
        lbl = self.config.get("target_time_label", "Tan làm")

        try:
            today_str = now.strftime("%Y-%m-%d")
            tgt_dt = datetime.strptime(f"{today_str} {tgt_str}", "%Y-%m-%d %H:%M:%S")
            diff = (tgt_dt - now).total_seconds()
            if diff < 0:
                tgt_dt += timedelta(days=1)
                diff = (tgt_dt - now).total_seconds()

            diff_sec = int(diff)
            h = diff_sec // 3600
            m = (diff_sec % 3600) // 60
            s = diff_sec % 60
            time_str = f"-{h:02d}:{m:02d}:{s:02d}"
        except Exception:
            diff_sec = 0
            time_str = "--:--:--"

        if self.config.get("dynamic_time_color", True):
            fg_col = self.get_dynamic_color_by_seconds(diff_sec)
        else:
            fg_col = self.config.get("text_color", "#00FFCC")

        prog_txt = ""
        if self.config.get("show_progress", True):
            pct = self.calculate_workday_progress(now)
            prog_txt = f" ({pct}%)"

        sub_txt = f"{mascot_prefix}🎯 ĐẾN {tgt_str[:5]} • {lbl}{prog_txt}"
        self.sub_label.configure(text=sub_txt, fg="#F59E0B")
        self.time_label.configure(text=time_str, fg=fg_col)
        self._check_and_resize(time_str, sub_txt)

    def _render_stopwatch_mode(self, mascot_prefix):
        if self.stopwatch_running:
            cur_elapsed = time.time() - self.stopwatch_start_time
        else:
            cur_elapsed = self.stopwatch_elapsed

        time_str = self._format_stopwatch_str(cur_elapsed)
        state_tag = "▶" if self.stopwatch_running else "⏸"
        lap_info = f" #{len(self.stopwatch_laps)} Laps" if self.stopwatch_laps else ""
        sub_txt = f"{mascot_prefix}⏱️ STOPWATCH • {state_tag}{lap_info}"

        if self.config.get("dynamic_time_color", True):
            fg_col = self.get_dynamic_color_by_seconds(cur_elapsed)
        else:
            fg_col = self.config.get("text_color", "#00FFCC")

        self.sub_label.configure(text=sub_txt, fg="#10B981")
        self.time_label.configure(text=time_str, fg=fg_col)
        self._check_and_resize(time_str, sub_txt)

    def _render_pomodoro_mode(self, mascot_prefix):
        if self.pomo_running:
            self.pomo_remaining -= 0.05
            if self.pomo_remaining <= 0:
                self.trigger_pomodoro_stage_complete()

        rem_sec = max(0, int(math.ceil(self.pomo_remaining)))
        m = rem_sec // 60
        s = rem_sec % 60
        time_str = f"{m:02d}:{s:02d}"

        if self.pomo_stage == "work":
            stage_str = f"🍅 TẬP TRUNG #{self.pomo_cycle_count + 1}"
            if self.config.get("dynamic_time_color", True):
                if rem_sec >= 15 * 60:
                    fg_col = "#EF4444"  # Đỏ
                elif rem_sec >= 5 * 60:
                    fg_col = "#F97316"  # Cam
                elif rem_sec >= 2 * 60:
                    fg_col = "#FBBF24"  # Vàng
                elif rem_sec >= 60:
                    fg_col = "#10B981"  # Xanh lá
                else:
                    fg_col = "#FFFFFF"  # Trắng
            else:
                fg_col = "#EF4444"
        elif self.pomo_stage == "break":
            stage_str = "☕ NGHỈ NGẮN (5P)"
            fg_col = "#10B981"
        else:
            stage_str = "🌴 NGHỈ DÀI (15P)"
            fg_col = "#38BDF8"

        state_tag = "▶" if self.pomo_running else "⏸"
        sub_txt = f"{mascot_prefix}{stage_str} {state_tag}"

        self.sub_label.configure(text=sub_txt, fg=fg_col)
        self.time_label.configure(text=time_str, fg=fg_col)
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

    # ---------------- 📐 POSITION & SIZING ----------------
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

    def set_text_color(self, color):
        self.config["text_color"] = color
        self.time_label.configure(fg=color)
        self.save_config()

    def pick_custom_color(self):
        chosen = colorchooser.askcolor(color=self.config["text_color"], title="Chọn màu chữ")[1]
        if chosen:
            self.set_text_color(chosen)

    def set_opacity(self, opacity):
        self.config["opacity"] = opacity
        self.root.attributes("-alpha", opacity)
        self.save_config()

    def set_font_size(self, size):
        self.config["font_size"] = size
        self.time_label.configure(font=("Consolas", size, "bold"))
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
            self.focus_sound_mgr.stop()
        except Exception:
            pass
        self.save_config()
        self.root.destroy()
        sys.exit(0)


def main():
    try:
        root = tk.Tk()
        root.title("Top Floating Multi-Clock")
        app = FloatingClock(root)
        root.mainloop()
    except Exception as e:
        import traceback
        err_msg = traceback.format_exc()
        try:
            messagebox.showerror("Floating Clock Error", f"Lỗi khởi động:\n\n{err_msg}")
        except Exception:
            print(f"Error: {err_msg}", file=sys.stderr)


if __name__ == "__main__":
    main()
