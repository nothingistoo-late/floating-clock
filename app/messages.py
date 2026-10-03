"""
Trung tâm quản lý toàn bộ câu nói động viên, thông báo, câu nhắc và lời thoại hiển thị trên màn hình.
Bạn có thể dễ dàng thêm bớt, chỉnh sửa nội dung tại đây mà không cần sửa code logic.
"""

# ====================================================================
# 💬 1. BỘ SƯU TẬP CÂU NÓI ĐỘNG VIÊN GENZ (THEO KHUNG GIỜ & NGỮ CẢNH)
# ====================================================================
MOTIVATIONAL_QUOTES = {
    # ☀️ Buổi sáng (6h - 11h)
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

    # 🍱 Buổi trưa (11h - 13h)
    "lunch": [
        "🍱 Sắp đến giờ cơm trưa rồi, nạp năng lượng rồi healing tiếp! 🍜",
        "🍜 Bụng đói là não overthinking liền, trưa nay làm bữa ngon nhé! 🍛",
        "🍛 Nghỉ tay đi ăn thôi fen, làm việc là phụ, ăn ngon là chính! 🤤",
        "🥗 Trưa nay làm cốc trà sữa full topping cho đời nó tươi! 🧋",
        "🍔 Nạp đạm nạp calo để chiều nay gánh team công ty nào! 🍟",
        "🍲 Ăn no căng bụng rồi chợp mắt 15 phút là đỉnh chóp! 😴",
        "🍗 Đừng nhịn ăn trưa nha fen, có thực mới vực được deadline! 🍕"
    ],

    # 💻 Buổi chiều (13h - 16h)
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

    # 🏃‍♂️ Chuẩn bị tan làm (16h - 18h)
    "leaving_soon": [
        "🏃‍♂️💨 Chỉ còn một chút nữa là tan làm rồi, đếm ngược giải phóng thôi!",
        "🍻 Sắp 17h45 rồi, dọn dẹp task chuẩn bị về quẩy thôi fen! 🎉",
        "🎉 Cố lên người anh em, sắp đến giờ về với tự do và healing rồi! 💆‍♂️",
        "🍺 Chiều nay làm cốc bia tươi hay đi lượn phố chill chill nào? 🍻",
        "🚴‍♂️ Sáng hướng nội, trưa hướng ngoại, chiều hướng về nhà! 🏠",
        "🏖️ Gom đồ vào balo, đếm từng giây chuẩn bị phóng như một cơn gió! 💨",
        "🍕 Tối nay ăn gì ngon để tự thưởng cho sự chăm chỉ hôm nay nhỉ? 🍔"
    ],

    # 🎉 Chiều Thứ 6 máu lửa
    "friday": [
        "🎉 Hôm nay THỨ 6 rồi! Chiều nay tan làm là quẩy tưng bừng cuối tuần!",
        "🏖️ Thứ 6 máu hơn thứ 2, tràn đầy hứng khởi về đích tuần này thôi! 🔥",
        "🍻 Thứ 6 vui vẻ! Chuẩn bị tinh thần xõa hết nấc thôi fen! 🏄‍♂️",
        "✨ Thứ 6 thần thánh: Deadline để tuần sau, tối nay là phải đi chill! 🍸"
    ],

    # ☀️ Thứ 7 về sớm
    "saturday": [
        "🏖️ Hôm nay THỨ 7 về sớm lúc 16h! Cuối tuần rực rỡ đang chờ đón!",
        "🏄‍♂️ Làm nốt buổi thứ 7 là được xõa hết mình rồi fen ơi! 🏖️",
        "☀️ Thứ 7 tan làm 16h: Về sớm đi dạo phố ngắm hoàng hôn thôi! 🌅"
    ],

    # 🌙 Buổi tối / Hết giờ làm (Sau 18h)
    "night": [
        "🎮 Đã hết giờ làm, tắt máy đi chill thôi fen!",
        "❤️ Giữ gìn sức khỏe nha fen, bạn đã vất vả cả ngày hôm nay rồi!",
        "🌙 Tối nay ngủ ngon giấc để mai nạp đầy năng lượng mới nhé! 🛌",
        "🛌 Đắp chăn ấm, lướt tóp tóp xíu rồi ngủ sớm nha fen! 😴"
    ]
}


# ====================================================================
# 🤖 2. CÂU LỆNH (PROMPT) GỬI CHO AI ĐỂ SINH CÂU NÓI GENZ
# ====================================================================
AI_PROMPT_TEMPLATE = (
    "Hãy tạo DUY NHẤT 1 câu động viên làm việc ngắn gọn (dưới 15 từ), cực kỳ hài hước, mang đậm phong cách GenZ Việt Nam "
    "(sử dụng linh hoạt từ ngữ trend như: slay, flex, healing, đỉnh nóc kịch trần, ting ting, chill, overthinking, hết nước chấm, bro, fen, gét gô...) "
    "phù hợp với ngữ cảnh: {context_tag}. Chỉ trả về duy nhất nội dung câu nói kèm icon biểu cảm (emoji), không thêm giải thích hay dấu ngoặc kép."
)


# ====================================================================
# 🔔 3. CÁC THÔNG BÁO POPUP & HỘP THOẠI CẢNH BÁO
# ====================================================================
ALERT_MESSAGES = {
    # ⏳ Hết giờ đếm ngược (Countdown Timer)
    "timer_finished_title": "⏳ Hết giờ đếm ngược!",
    "timer_finished_body": "⏳ ĐÃ HẾT GIỜ ĐẾM NGƯỢC!",

    # 🎯 Đến mốc giờ mục tiêu / Tan làm
    "target_reached_title": "🎯 Đã đến mốc giờ: {time_str}",
    "target_reached_body": "🎯 ĐÃ ĐẾN MỐC THỜI GIAN: {time_str}\n\n🎉 {label} 🎉\nChúc fen buổi chiều/tối tràn ngập niềm vui!",

    # ⏰ Chuông báo thức
    "alarm_title": "⏰ Báo thức: {time_str}",
    "alarm_body": "⏰ ĐÃ ĐẾN GIỜ BÁO THỨC!\n\n[{time_str}] {label}",
    "alarm_snooze_label": "(Báo lại 5p) {label}",

    # 🍅 Pomodoro
    "pomo_work_complete_title": "🍅 Pomodoro - Giờ nghỉ ngơi",
    "pomo_short_break_body": "🍅 Hoàn thành tập trung! Đến lúc NGHỈ NGẮN 5 phút thư giãn.",
    "pomo_long_break_body": "🍅 Hoàn thành phiên #{cycle}! Đến lúc NGHỈ DÀI 15 phút rồi.",
    "pomo_break_complete_title": "🍅 Pomodoro - Bắt đầu làm việc",
    "pomo_break_complete_body": "⚡ Hết giờ nghỉ! Bạn đã sẵn sàng cho phiên tập trung tiếp theo chưa?",

    # 💧 Nhắc uống nước & Vươn vai
    "hydration_title": "💧 Nhắc Nhở Sức Khỏe",
    "hydration_header": "UỐNG NƯỚC & VƯƠN VAI NÀO FEN!",
    "hydration_body": "Ngồi máy tính lâu rồi, uống 1 ngụm nước, chớp mắt và đứng dậy xoay cổ tay vươn vai xíu nhé!",
    "hydration_btn": "✨ Đã uống nước & khỏe re!"
}


# ====================================================================
# 💸 4. TRẠNG THÁI HIỂN THỊ TIỀN LƯƠNG TRÊN MÀN HÌNH
# ====================================================================
SALARY_TEXTS = {
    "hidden_daily": "💸 Ngày: •••••• đ",
    "hidden_month": "📅 {cycle_label}: •••••• đ",
    "weekend": "💸 Ngày: Nghỉ cuối tuần 🌴",
    "before_work": "💸 Ngày: Chuẩn bị làm việc ({start_time}) ☕",
    "lunch_break": "🍱 Giờ nghỉ trưa",
    "after_work": "Đã tan làm 🎉",
}


# ====================================================================
# 📅 5. DANH SÁCH CÁC NGÀY LỄ LỚN TRONG NĂM
# ====================================================================
HOLIDAYS_DATA = [
    {"name": "🎆 Tết Dương Lịch", "month": 1, "day": 1},
    {"name": "🧧 Tết Nguyên Đán (Âm Lịch)", "month": 2, "day": 17},
    {"name": "👑 Giỗ Tổ Hùng Vương (10/3 Âm)", "month": 4, "day": 26},
    {"name": "🇻🇳 Thống Nhất & Lao Động (30/4 - 1/5)", "month": 4, "day": 30},
    {"name": "⭐ Quốc Khánh Việt Nam (2/9)", "month": 9, "day": 2},
    {"name": "🎄 Lễ Giáng Sinh (Noel 25/12)", "month": 12, "day": 25}
]
