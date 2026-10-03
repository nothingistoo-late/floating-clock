"""
Constants and definitions for Top Floating Clock
"""

# Win32 API Constants for Click-through and Extended Styles
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020

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

# 💬 GENZ MOTIVATION & QUOTES POOL (OFFLINE & CLOUD)
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
