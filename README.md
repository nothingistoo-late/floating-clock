# 🕒 Top Floating Multi-Clock (Đồng Hồ Nổi Ghim Đỉnh Màn Hình Đa Năng)

Ứng dụng đồng hồ nổi chuyên nghiệp (Floating Always-On-Top Multi-Clock), siêu nhẹ, mượt mà, tích hợp đầy đủ các chế độ: **Đồng hồ thời gian thực, Đếm ngược, Đếm đến mốc giờ, Báo thức thông minh, Bấm giờ thể thao, Pomodoro Focus, Bộ đếm tiền lương nhảy theo giây, Focus MIT Task, và Giám sát CPU/RAM**.

---

## ✨ Các Chế Độ & Tính Năng Đỉnh Cao

1. **🕒 Đồng Hồ Thời Gian Thực (Realtime Clock)**:
   - Hiển thị chuẩn xác `HH:MM:SS`, hỗ trợ chế độ 12h/24h, mili-giây (`.ms`).
   - Tự động hiển thị Thứ & Ngày tháng (`T5, 02/10/2026`).
   - Huy hiệu báo thức thông minh (hiển thị mốc báo thức gần nhất sắp tới).

2. **⏳ Đếm Ngược (Countdown Timer)**:
   - Các nút cài nhanh: 1m, 3m, 5m, 10m, 15m, 25m, 30m, 1h hoặc nhập tùy ý theo Giờ:Phút:Giây.
   - Nhấp đúp chuột hoặc bấm `Space` để Bắt đầu / Tạm dừng / Tiếp tục.
   - Khi còn dưới 10 giây: Đổi màu cảnh báo trực quan.
   - Khi hết giờ: **Chuông báo thức réo rắt + Viền nhấp nháy + Hộp thoại thông báo nổi bật** (có nút Tắt chuông hoặc Lặp lại).

3. **🎯 Đếm Ngược Tan Làm Tự Động (Work Departure Schedule)**:
   - Tự động nhận diện thứ trong tuần:
     - **Thứ 2 đến Thứ 6 (T2 - T6)**: Mặc định **`17:45`**
     - **Riêng Thứ 7**: Mặc định **`16:00`** (về sớm)
   - Cho phép tự do chỉnh lại mốc giờ trong Bảng điều khiển (Control Center).
   - Tự động đếm ngược thời gian còn lại: `Còn -01:23:45`.
   - Khi đến đúng mốc giờ: Chuông reo thông báo chúc mừng đã đến giờ về!

4. **💸 Realtime Salary Ticker (Bộ Đếm Tiền Lương 2 Dòng: Ngày & Tháng)**:
   - **Dòng 1 (Theo ngày)**: Tích lũy tiền lương kiếm được hôm nay nhảy theo từng giây (`💸 Ngày: +125.430 đ`).
   - **Dòng 2 (Theo tháng)**: Tổng tiền lương tích lũy từ đầu tháng đến hiện tại + phần trăm tháng (`📅 Tháng: 4.825.430 đ (32.1%)`).
   - Tùy chỉnh lương tháng, số ngày làm việc/tháng, số giờ làm việc/ngày, bật/tắt từng dòng theo ý muốn.
   - Chế độ riêng tư: Bấm phím **`S`** (hoặc click vào dòng lương) để ẩn/hiện (`💸 •••••• đ`).

5. **🎯 Focus MIT Task (Mục Tiêu Quan Trọng Nhất Hôm Nay)**:
   - Giữ 1 nhiệm vụ trọng tâm duy nhất hiển thị cạnh đồng hồ để chống xao nhãng.
   - Bấm phím **`T`** hoặc nhấp chuột vào dòng task để mở hộp thoại cập nhật / đánh dấu hoàn thành.

6. **📅 Payday & Holiday Milestones (Đếm Ngược Ngày Nhận Lương & Dịp Lễ)**:
   - Đếm ngược chính xác số ngày tới kỳ nhận lương định kỳ (ví dụ mùng 5 hàng tháng).
   - Bảng theo dõi các kỳ nghỉ lễ lớn tại Việt Nam: Tết Dương Lịch, Tết Nguyên Đán, Giỗ Tổ Hùng Vương, 30/4 - 1/5, Quốc Khánh 2/9, Giáng Sinh...

7. **📊 Realtime Win32 System Monitor (Giám Sát CPU & RAM %)**:
   - Đo lường mức sử dụng CPU & RAM theo thời gian thực bằng Win32 Ctypes thuần túy (siêu nhẹ, không tốn tài nguyên).

8. **🚀 Khởi Động Cùng Windows (Start with Windows)**:
   - Tích hợp Windows Registry, tự động chạy cùng hệ điều hành mỗi khi mở máy.

9. **🧲 Tự Động Làm Mờ Khi Rời Chuột (Auto-Fade / Auto-Hide - Phím `H`)**:
   - Khi không rê chuột vào widget, đồng hồ tự động mờ đi nhẹ nhàng để không che khuất tài liệu hay màn hình làm việc.

10. **🤖 AI Động Viên GenZ & Motivational Quotes**:
    - **Hỗ trợ Groq (gsk_...)**, **Google Gemini**, **OpenAI**, hoặc **OpenRouter** để AI tự động sáng tạo vô số câu GenZ hài hước theo thời gian thực (*slay, flex, healing, đỉnh nóc kịch trần, ting ting, chill, overthinking...*).
    - **Kho 50+ câu GenZ Offline** tích hợp sẵn khi không có mạng.
    - Nhấp chuột trực tiếp vào dòng chữ để gọi AI tạo ngay câu mới!

11. **💧 Nhắc Nhở Uống Nước & Vươn Vai (Hydration Reminder)**:
    - Tự động phát chuông Ding-dong êm dịu và hiện popup nhắc nhở sau mỗi 45 phút ngồi máy tính.

12. **⏰ Báo Thức Đa Năng (Smart Multi-Alarms)**:
    - Đặt không giới hạn các mốc báo thức kèm ghi chú, hỗ trợ Snooze 5 phút.

13. **⏱️ Bấm Giờ Thể Thao (Stopwatch) & 🍅 Pomodoro (Focus Timer)**:
    - Stopwatch đo chuẩn 1/100s, ghi vòng Lap.
    - Pomodoro 25m Focus / 5m Break / 15m Long Break.

14. 🔍 **Chế Độ Thu Nhỏ Tối Giản (Mini Compact Mode - Phím `M`)**:
    - Thu nhỏ đồng hồ về dạng capsule siêu gọn gàng, ẩn mọi text phụ, chỉ hiện duy nhất số giờ.

15. 🌈 **Tự Động Đổi Màu Theo Thời Gian (Dynamic Time Color - Phím `D`)**:
    - Màu sắc số giờ sẽ tự động biến đổi sống động:
      - 🔴 **$\ge$ 8 tiếng**: Màu Đỏ (`#EF4444`)
      - 🟠 **$\ge$ 5 tiếng**: Màu Cam (`#F97316`)
      - 🟡 **$\ge$ 2 tiếng**: Màu Vàng (`#FBBF24`)
      - 🟢 **$\ge$ 1 tiếng**: Màu Xanh lá (`#10B981`)
      - ⚪ **$<$ 1 tiếng**: Màu Trắng sáng Neon (`#FFFFFF`)

16. 🌦️ **Dự Báo Thời Tiết Realtime (Open-Meteo Weather - Phím `W`)**:
    - Tự động cập nhật nhiệt độ & thời tiết thực tế cho các tỉnh thành Việt Nam (Hà Nội, TP.HCM, Đà Nẵng, Hải Phòng, Cần Thơ, Nha Trang, Đà Lạt, Huế, Vũng Tàu, Quy Nhơn...).
    - Hiển thị trực quan: `🌤️ Hà Nội: 32°C • Có mây` ngay trên HUD.
    - Nhấp chuột hoặc bấm phím **`W`** để mở thẻ dự báo chi tiết (nhiệt độ, gió, độ ẩm, tình trạng mây/mưa...).
    - Hoàn toàn miễn phí, tốc độ cực nhanh, không cần đăng ký API Key.

17. 🎧 **Âm Thanh Tập Trung / White Noise Generator (Phím `F9`)**:
    - Trình phát âm thanh nền thư giãn giúp kích hoạt trạng thái Deep Work & tăng khả năng tập trung:
      - 🌧️ **Mưa rào êm dịu (Rainfall)**
      - 🌊 **Sóng biển dạt dào (Ocean Waves)**
      - 🧘 **Tiếng ồn nâu sâu lắng (Brown Noise)**
      - 📻 **Tiếng ồn trắng tĩnh tâm (White Noise)**
      - 🧠 **Sóng não Alpha 432Hz (Deep Focus & Relax)**
      - ☕ **Quán cà phê chill (Cafe Ambient)**
    - Tự động tổng hợp âm thanh đa tầng bằng thuật toán (Procedural Audio Synthesis), phát lặp vô tận, không cần tải file âm thanh nặng từ ngoài.
    - Bấm phím **`F9`** để Bật / Tắt tức thì ở bất kỳ lúc nào!

---

## ⌨️ Phím Tắt & Thao Tác Nhanh

| Thao Tác | Phím Tắt | Chức Năng |
| :--- | :--- | :--- |
| **Kéo Chuột Trái** | `Mouse 1 Drag` | Di chuyển vị trí đồng hồ tới bất kỳ đâu trên màn hình |
| **Nhấp Đúp Chuột** | `Double Click` | Thu nhỏ / Phóng to (Mini Mode) hoặc Start/Pause (Timer/Stopwatch/Pomodoro) |
| **Chuột Phải** | `Right Click` | Mở Menu ngữ cảnh đầy đủ chức năng |
| **Phím `F9`** | `F9` | **Bật / Tắt nhanh Âm thanh tập trung (White Noise / Mưa / Sóng biển)** 🎧 |
| **Phím `W`** | `W` | **Xem nhanh bảng Dự báo thời tiết Realtime** 🌦️ |
| **Phím `M`** | `M` | Bật / Tắt chế độ Thu nhỏ tối giản (Mini Mode - chỉ hiện số giờ) |
| **Phím `D`** | `D` | Bật / Tắt chế độ Tự động đổi màu theo thời gian (Dynamic Color) |
| **Phím `S`** | `S` | Ẩn / Hiện số tiền lương (Chế độ riêng tư `💸 •••••• đ`) |
| **Phím `T`** | `T` | Mở nhanh hộp thoại Task trọng tâm hôm nay (Focus MIT) |
| **Phím `H`** | `H` | Bật / Tắt tự động làm mờ khi rời chuột (Auto-fade/hide) |
| **Phím `F2`** | `F2` | Chuyển nhanh qua lại giữa các Chế độ (Clock ⇄ Timer ⇄ Target ⇄ Stopwatch ⇄ Pomodoro) |
| **Phím `F8`** | `F8` | Bật / Tắt chế độ Xuyên thấu chuột (Click-through) |
| **Phím `Space`** | `Space` | Start / Pause nhanh trong chế độ Timer hoặc Stopwatch |

---

## 🚀 Cách Khởi Động

- **Cách 1 (Khuyên dùng - File EXE độc lập)**: Nhấp đúp chuột trực tiếp vào file **`FloatingClock.exe`** (chạy ngay lập tức, không cần cài môi trường Python).
- **Cách 2**: Nhấp đúp chuột vào file **`run_clock.bat`** (chạy ẩn ngầm bằng `pythonw`, không hiện cửa sổ đen cmd).
- **Cách 3**: Chạy lệnh `python floating_clock.py`.
