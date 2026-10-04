# TOOL THEO DÕI & BÁO SỰ KIỆN ĐIỂM RÈN LUYỆN IUH QUA TELEGRAM

Hệ thống tự động kiểm tra liên tục cổng Đoàn Thanh niên IUH (`doantn.iuh.edu.vn`), phát hiện ngay khi có sự kiện mở thêm slot hoặc có người huỷ đăng ký để gửi chuông cảnh báo và tin nhắn Telegram về điện thoại của bạn.

---

## 🚀 TÍNH NĂNG NỔI BẬT

1. **Quét liên tục:** Tự động gửi request kiểm tra danh sách sự kiện mỗi 15-30 giây (tùy chỉnh được).
2. **Cảnh báo tức thời:** Khi phát hiện một sự kiện có slot trống (`current < max` hoặc có nút đăng ký), bot lập tức gửi tin nhắn khẩn cấp về Telegram kèm link bấm vào đăng ký ngay.
3. **Phát chuông báo động:** Kêu chuông tít tít trên máy tính (Windows Beep) để nếu bạn đang ngồi máy tính thì chuyển tab đăng ký tức thì.
4. **Báo cáo định kỳ (Heartbeat):** Sau mỗi 30-60 phút sẽ gửi 1 tin nhắn tổng kết danh sách sự kiện hiện có, giúp bạn yên tâm tool vẫn đang chạy ổn định.
5. **Cảnh báo Cookie hết hạn:** Tự động phát hiện khi phiên đăng nhập hết hạn và gửi thông báo nhắc bạn cập nhật lại cookie.
6. **Chống spam thông minh:** Không gửi lặp lại hàng trăm tin nhắn nếu sự kiện đó vẫn đang mở, chỉ gửi lại khi số lượng slot thay đổi hoặc sau thời gian cooldown.

---

## 🛠 HƯỚNG DẪN CÀI ĐẶT & SỬ DỤNG (3 BƯỚC)

### Bước 1: Tạo Bot Telegram & Lấy Chat ID

1. **Tạo Bot Telegram:**
   - Mở ứng dụng Telegram trên điện thoại hoặc máy tính.
   - Tìm kiếm bot: `@BotFather` (có tích xanh).
   - Gửi lệnh: `/newbot`
   - Đặt tên cho bot (ví dụ: `IUH Alert Bot`).
   - Đặt username cho bot (phải kết thúc bằng chữ `bot`, ví dụ: `iuh_drl_alert_bot`).
   - Copy mã **HTTP API Token** (dạng `123456789:AAHxxxxx...`).

2. **Lấy Chat ID:**
   - **Nếu nhận tin nhắn riêng:** Tìm kiếm bot `@userinfobot` trên Telegram ➔ Nhấn `/start` ➔ Lấy `Id: 6361097282`. Nhớ nhắn `/start` với bot của bạn trước 1 lần.
   - **Nếu dùng trong Nhóm chung (Group/Channel):**
     * Tạo 1 nhóm Telegram, thêm Bot của bạn vào nhóm và set quyền **Admin** (để bot có quyền Ghim tin nhắn Ping All).
     * Mời bot `@RawDataBot` hoặc `@userinfobot` vào nhóm để xem `chat.id` của nhóm (thường bắt đầu bằng `-100...`, ví dụ: `-1002345678901`).
     * Sau khi lấy ID nhóm thì kick bot lấy ID ra.
   - **Có thể điền nhiều ID:** Điền cả ID cá nhân và ID nhóm cách nhau bằng dấu phẩy: `6361097282, -1002345678901`.

---

### Bước 2: Lấy Cookie `PHPSESSID` từ trình duyệt

1. Dùng trình duyệt (Chrome / Cốc Cốc / Edge / Firefox) truy cập: `https://doantn.iuh.edu.vn/login.html`
2. Đăng nhập tài khoản sinh viên của bạn.
3. Vào trang: `https://doantn.iuh.edu.vn/doanvien.html@211@Tra-cuu` (trang có bảng danh sách sự kiện).
4. Nhấn phím **F12** (hoặc chuột phải -> chọn **Kiểm tra / Inspect**).
5. Chuyển sang tab **Application** (Ứng dụng) -> bên cột trái chọn mục **Cookies** -> click vào `https://doantn.iuh.edu.vn`.
6. Tìm dòng có tên là `PHPSESSID` -> nhấp đúp vào cột **Value** -> Copy toàn bộ chuỗi giá trị này (dạng chữ và số, ví dụ `5bs14k05j64875pqmfrf0orqet`).

---

### Bước 3: Điền cấu hình vào file `.env`

Mở file `.env` trong thư mục bằng Notepad hoặc VS Code, điền các thông tin đã lấy:

```env
TELEGRAM_BOT_TOKEN=123456789:AAHxxxxxx...
TELEGRAM_CHAT_ID=987654321
PHPSESSID=5bs14k05j64875pqmfrf0orqet

# Tần suất kiểm tra (giây) - Mặc định 20s
CHECK_INTERVAL_SECONDS=20

# Tần suất gửi báo cáo định kỳ (phút) - Mặc định 60 phút
STATUS_UPDATE_MINUTES=60

# Chuông báo động trên máy tính: True / False
SOUND_ALERT=True
```

---

## ▶️ CHẠY CHƯƠNG TRÌNH

1. **Kiểm tra kết nối trước:**
   - Click đúp vào file `test.bat` (hoặc chạy lệnh `python test_connection.py` trong terminal).
   - Tool sẽ kiểm tra xem Telegram Bot có gửi được tin không và Cookie có lấy được bảng sự kiện không.

2. **Chạy chính thức:**
   - Click đúp vào file `run.bat` (hoặc chạy lệnh `python main.py`).
   - Cửa sổ console sẽ hiển thị nhật ký quét liên tục.
   - Khi có bất kỳ sự kiện nào còn slot trống, bot sẽ lập tức bắn tin nhắn về điện thoại của bạn!
