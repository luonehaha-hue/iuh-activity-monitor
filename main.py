import sys
from config import Config
from logging_config import configure_logging
from monitor import DRLMonitor

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def main():
    configure_logging()
    # Kiem tra cau hinh ban dau
    if not Config.TELEGRAM_BOT_TOKEN or not Config.TELEGRAM_CHAT_ID:
        print("[LỖI KHỞI ĐỘNG] Bạn chưa cấu hình TELEGRAM_BOT_TOKEN hoặc TELEGRAM_CHAT_ID!")
        print("Vui lòng mở file .env để điền thông tin trước khi chạy.")
        print("Mẹo: Chạy 'python test_connection.py' để kiểm tra kết nối.")
        return 1

    if not Config.PHPSESSID:
        print("[LỖI KHỞI ĐỘNG] Bạn chưa điền PHPSESSID trong file .env!")
        print("Vui lòng lấy Cookie phiên đăng nhập từ trình duyệt và dán vào file .env.")
        print("Mẹo: Đăng nhập https://doantn.iuh.edu.vn -> F12 -> tab Application -> Cookies -> PHPSESSID")
        return 1

    monitor = DRLMonitor()
    monitor.run_forever()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
