"""
Constants and definitions for Top Floating Clock
"""

# Win32 API Constants for Click-through and Extended Styles
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
# Tool window: không nút taskbar, không xuất hiện trong Alt+Tab
WS_EX_TOOLWINDOW = 0x00000080
# App window: ép cửa sổ lên taskbar — cần gỡ bỏ
WS_EX_APPWINDOW = 0x00040000

# Win32 Hotkey Constants
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000
VK_F8 = 0x77

# Danh mục tọa độ kinh độ - vĩ độ các thành phố lớn tại Việt Nam
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

# Ánh xạ mã thời tiết Open-Meteo (WMO Weather interpretation codes)
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

from app.messages import MOTIVATIONAL_QUOTES

# 💬 GENZ MOTIVATION & QUOTES POOL (OFFLINE & CLOUD) - alias to app.messages
DEFAULT_QUOTES = MOTIVATIONAL_QUOTES

