"""
Configuration manager for Top Floating Clock
"""
import copy
import json
import os
import sys

if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
    BUNDLE_DIR = getattr(sys, '_MEIPASS', APP_DIR)
else:
    # app/config.py is in app/, root project dir is parent
    APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    BUNDLE_DIR = APP_DIR

CONFIG_FILE = os.path.join(APP_DIR, "clock_config.json")

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
    "dynamic_time_color": True,      # Tự động đổi màu theo thời gian
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
    "holidays": [
        {"name": "🎆 Tết Dương Lịch", "month": 1, "day": 1},
        {"name": "🧧 Tết Nguyên Đán (Âm Lịch)", "month": 2, "day": 17},
        {"name": "👑 Giỗ Tổ Hùng Vương (10/3 Âm)", "month": 4, "day": 26},
        {"name": "🇻🇳 Thống Nhất & Lao Động (30/4 - 1/5)", "month": 4, "day": 30},
        {"name": "⭐ Quốc Khánh Việt Nam (2/9)", "month": 9, "day": 2},
        {"name": "🎄 Lễ Giáng Sinh (Noel 25/12)", "month": 12, "day": 25}
    ],
    # System Monitor (CPU & RAM)
    "show_sys_monitor": False,
    # Auto-Hide on edge (Tự thu gọn khi rời chuột)
    "auto_hide": False,
    # Weather Forecast (Dự báo thời tiết Open-Meteo)
    "weather": {
        "enabled": True,
        "city_name": "Hà Nội",
        "lat": 21.0285,
        "lon": 105.8542,
        "auto_refresh_min": 30
    },
    # Focus Ambient Sound (Âm thanh nền tập trung / Nhạc stream)
    "focus_sound": {
        "enabled": False,
        "sound_type": "rain",
        "custom_url": "",
        "volume": 50
    }
}


def deep_merge(base, override):
    """
    Hòa trộn đệ quy cấu hình override vào base để đảm bảo không bị thiếu key con
    khi người dùng nâng cấp từ phiên bản cũ.
    """
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def load_config():
    """Tải file config hoặc trả về cấu hình mặc định"""
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    cfg = deep_merge(cfg, data)
        except Exception:
            pass
    return cfg


def save_config(config_dict):
    """Lưu cấu hình ra file JSON an toàn"""
    try:
        temp_file = CONFIG_FILE + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(config_dict, f, indent=4, ensure_ascii=False)
        # Atomically replace or rename
        if os.path.exists(CONFIG_FILE):
            os.replace(temp_file, CONFIG_FILE)
        else:
            os.rename(temp_file, CONFIG_FILE)
        return True
    except Exception:
        # Fallback direct write
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config_dict, f, indent=4, ensure_ascii=False)
            return True
        except Exception:
            return False
