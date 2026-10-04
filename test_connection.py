import sys
import datetime
import requests
import urllib3
from config import Config
from parser import parse_events
from telegram_bot import send_telegram_message

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def test_all():
    print("=" * 60)
    print("KIỂM TRA CẤU HÌNH & KẾT NỐI (TEST CONNECTION)")
    print("=" * 60)

    # 1. Kiem tra file .env
    print("\n[1/3] Kiểm tra file cấu hình .env:")
    token_status = "Đã cấu hình" if Config.TELEGRAM_BOT_TOKEN else "Chưa điền"
    print(f"  - Telegram Bot Token: {token_status}")
    print(f"  - Telegram Chat ID  : {', '.join(Config.TELEGRAM_CHAT_IDS) or '(Chưa điền)'}")
    cookie_status = "Đã cấu hình" if Config.PHPSESSID else "Chưa điền"
    print(f"  - Cookie PHPSESSID  : {cookie_status}")

    # 2. Test Telegram
    print("\n[2/3] Kiểm tra gửi tin nhắn thử nghiệm qua Telegram:")
    if not Config.TELEGRAM_BOT_TOKEN or not Config.TELEGRAM_CHAT_ID:
        print("  ❌ THẤT BẠI: Bạn chưa điền TELEGRAM_BOT_TOKEN hoặc TELEGRAM_CHAT_ID trong file .env!")
    else:
        now_str = datetime.datetime.now().strftime("%H:%M:%S - %d/%m/%Y")
        test_msg = (
            "🔔 <b>TEST KẾT NỐI THÀNH CÔNG!</b>\n\n"
            f"⏰ Thời gian: <i>{now_str}</i>\n"
            "Bot thông báo Điểm rèn luyện IUH đã kết nối thành công với tài khoản Telegram của bạn!"
        )
        personal_ids = [cid for cid in Config.TELEGRAM_CHAT_IDS if not str(cid).startswith("-")]
        ok = send_telegram_message(test_msg, target_chat_ids=personal_ids)
        if ok:
            print("  ✅ THÀNH CÔNG: Đã gửi tin nhắn test tới Telegram! Hãy kiểm tra app Telegram của bạn.")
        else:
            print("  ❌ THẤT BẠI: Không thể gửi tin nhắn Telegram. Vui lòng kiểm tra lại Token hoặc Chat ID.")

    # 3. Test Cookie & Crawl IUH
    print("\n[3/3] Kiểm tra kết nối tới cổng Đoàn Thanh niên IUH:")
    if not Config.PHPSESSID:
        print("  ⚠️ CHƯA CÓ COOKIE: Bạn chưa điền PHPSESSID trong file .env.")
        print("     Hãy mở trình duyệt -> đăng nhập doantn.iuh.edu.vn -> F12 -> Application -> Cookies để lấy PHPSESSID.")
    else:
        try:
            session = requests.Session()
            session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                "Referer": "https://doantn.iuh.edu.vn/home.html"
            })
            session.cookies.set("PHPSESSID", Config.PHPSESSID, domain="doantn.iuh.edu.vn")

            resp = session.get(Config.URL_TRA_CUU, timeout=15, verify=False)
            if resp.status_code != 200:
                print(f"  ❌ Lỗi kết nối HTTP: Mã {resp.status_code}")
                return

            success, events, msg = parse_events(resp.text, base_url=Config.URL_TRA_CUU)
            if not success:
                print(f"  ❌ COOKIE KHÔNG HỢP LỆ: {msg}")
            else:
                print(f"  ✅ ĐĂNG NHẬP THÀNH CÔNG! Đã lấy được bảng sự kiện:")
                print(f"     Tìm thấy {len(events)} sự kiện:")
                for i, ev in enumerate(events, 1):
                    slots = f"{ev['current_slots']}/{ev['max_slots']}" if ev['max_slots'] else ev['status_text']
                    avail_txt = "🔥 CÒN CHỖ!" if ev['is_available'] else "🔴 Đã full"
                    loc_txt = f" | {ev['location']}" if ev.get('location') else ""
                    print(f"     {i}. [{slots}] {ev['title']} ({avail_txt} | +{ev['points']}đ{loc_txt})")

        except Exception as e:
            print(f"  ❌ Lỗi khi gửi request: {e}")

    print("\n" + "=" * 60)
    print("HOÀN TẤT KIỂM TRA.")
    print("Nếu mọi thứ đều ✅, bạn có thể chạy: python main.py")
    print("=" * 60)

if __name__ == "__main__":
    test_all()
