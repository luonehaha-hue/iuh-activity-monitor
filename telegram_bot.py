import html
import requests
import datetime
import sys
import logging
from config import Config

logger = logging.getLogger("telegram")
_http = requests.Session()

def send_telegram_message(
    text: str,
    parse_mode: str = "HTML",
    disable_preview: bool = True,
    pin_if_group: bool = False,
    target_chat_ids: list = None,
    disable_notification: bool = False,
) -> bool:
    """
    Gui tin nhan den cac chat_id duoc chi dinh (hoac mac dinh toan bo TELEGRAM_CHAT_IDS).
    Neu la nhom (chat_id bat dau bang dau -) va pin_if_group=True, tu dong ghim tin nhan de ping all toan bo thanh vien.
    """
    token = Config.TELEGRAM_BOT_TOKEN
    chat_ids = target_chat_ids if target_chat_ids is not None else Config.TELEGRAM_CHAT_IDS

    if not token or not chat_ids or token == "YOUR_BOT_TOKEN_HERE":
        logger.error("Chưa cấu hình TELEGRAM_BOT_TOKEN hoặc TELEGRAM_CHAT_ID trong .env")
        return False

    url_send = f"https://api.telegram.org/bot{token}/sendMessage"
    url_pin = f"https://api.telegram.org/bot{token}/pinChatMessage"

    overall_success = False

    for cid in chat_ids:
        payload = {
            "chat_id": cid,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_preview,
            "disable_notification": disable_notification,
        }

        try:
            resp = _http.post(url_send, json=payload, timeout=10)
            data = resp.json()
            if data.get("ok"):
                overall_success = True
                msg_id = data["result"]["message_id"]

                # Neu la nhom va yeu cau pin
                is_group = str(cid).startswith("-")
                if is_group and pin_if_group and Config.PIN_ALERT_IN_GROUP:
                    try:
                        _http.post(url_pin, json={
                            "chat_id": cid,
                            "message_id": msg_id,
                            "disable_notification": False  # Bat chuong thong bao toan nhom
                        }, timeout=5)
                    except Exception:
                        pass
            else:
                migrated_chat_id = data.get("parameters", {}).get("migrate_to_chat_id")
                if migrated_chat_id:
                    retry_payload = dict(payload)
                    retry_payload["chat_id"] = migrated_chat_id
                    retry_response = _http.post(url_send, json=retry_payload, timeout=10)
                    retry_data = retry_response.json()
                    if retry_data.get("ok"):
                        overall_success = True
                        logger.info("Nhóm đã nâng cấp thành supergroup; gửi lại thành công.")
                    else:
                        logger.error("Telegram từ chối tin nhắn sau khi chuyển sang supergroup: %s", retry_data.get("description"))
                else:
                    logger.error("Telegram từ chối tin nhắn tới chat %s: %s", cid, data.get("description"))
        except (requests.RequestException, ValueError, KeyError) as exc:
            # Không log URL exception vì URL Telegram chứa bot token.
            logger.error("Telegram gửi tới chat %s thất bại (%s).", cid, type(exc).__name__)

    return overall_success


def play_alert_sound():
    """
    Phat am thanh bip tren may tinh (Windows) de gay chu y khi co slot trong.
    """
    if not Config.SOUND_ALERT:
        return

    if sys.platform == "win32":
        try:
            import winsound
            winsound.Beep(1200, 150)
            winsound.Beep(1600, 150)
            winsound.Beep(2000, 300)
        except Exception:
            pass


def _build_slot_alert_text(event: dict, is_full: bool = False) -> str:
    title = html.escape(event.get("title", "Không rõ"))
    curr = event.get("current_slots")
    total = event.get("max_slots")
    avail = event.get("available_slots")
    pts = html.escape(str(event.get("points", "0")))
    dl = html.escape(str(event.get("deadline", "Chưa rõ")))

    loc = html.escape(event.get("location", ""))
    ev_time = html.escape(event.get("event_time", ""))

    reg_url = event.get("register_url")
    if not reg_url:
        reg_url = Config.URL_TRA_CUU

    # Dong ty le slot
    if curr is not None and total is not None:
        if is_full:
            slot_line = f"👥 <b>{curr} / {total}</b>  →  <b>ĐÃ HẾT CHỖ</b>"
        else:
            slot_line = f"👥 <b>{curr} / {total}</b>  →  <b>CÒN {avail} CHỖ</b>"
    else:
        status = html.escape(event.get("status_text", ""))
        slot_line = f"⚡ Trạng thái: <b>{status}</b>"

    # Phan dia diem & thoi gian hien truc tiep
    extra_details = []
    if loc:
        extra_details.append(f"📍 {loc}")
    if ev_time:
        extra_details.append(f"🕔 Thời gian tổ chức: <b>{ev_time}</b>")

    details_block = ""
    if extra_details:
        details_block = "\n".join(extra_details) + "\n\n"

    headline = "🔴 <b>SLOT ĐÃ HẾT</b>" if is_full else "🔥 <b>SLOT ĐRL VỪA MỞ</b>"
    mention = "" if is_full else "@everyone\n"
    return (
        f"{mention}"
        f"{headline}\n\n"
        f"<b>{title}</b>\n"
        "━━━━━━━━━━━━━━\n"
        f"{slot_line}\n"
        f"🏆 <b>+{pts} điểm</b>\n"
        f"📅 Hạn đăng ký: <b>{dl}</b>\n\n"
        f"{details_block}"
        f"👉 <a href=\"{reg_url}\"><b>Đăng ký ngay</b></a>"
    )


def send_slot_alert(event: dict, target_chat_ids: list = None, play_sound: bool = True) -> bool:
    """Gửi một cảnh báo slot mới."""
    msg = _build_slot_alert_text(event)

    if play_sound:
        play_alert_sound()
    return send_telegram_message(
        msg,
        disable_preview=True,
        pin_if_group=False,
        target_chat_ids=target_chat_ids,
    )


def upsert_slot_alert(
    event: dict,
    target_chat_ids: list,
    message_refs: dict = None,
    is_full: bool = False,
    create_if_missing: bool = True,
):
    """Tạo cảnh báo lần đầu hoặc edit tin cũ khi số slot thay đổi."""
    refs = dict(message_refs or {})
    text = _build_slot_alert_text(event, is_full=is_full)
    api_base = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}"
    overall_success = False

    for configured_chat_id in target_chat_ids:
        key = str(configured_chat_id)
        reference = refs.get(key, {})
        actual_chat_id = reference.get("chat_id", configured_chat_id)
        message_id = reference.get("message_id")

        if message_id:
            try:
                response = _http.post(
                    f"{api_base}/editMessageText",
                    json={
                        "chat_id": actual_chat_id,
                        "message_id": message_id,
                        "text": text,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": True,
                    },
                    timeout=10,
                ).json()
                description = str(response.get("description", "")).lower()
                if response.get("ok") or "message is not modified" in description:
                    overall_success = True
                    continue
                logger.warning("Không thể edit cảnh báo slot cũ; sẽ tạo tin mới nếu được phép.")
            except (requests.RequestException, ValueError):
                logger.warning("Edit cảnh báo slot cũ thất bại; sẽ tạo tin mới nếu được phép.")

        if not create_if_missing:
            continue

        payload = {
            "chat_id": configured_chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
            "disable_notification": False,
        }
        try:
            response = _http.post(f"{api_base}/sendMessage", json=payload, timeout=10).json()
            migrated_chat_id = response.get("parameters", {}).get("migrate_to_chat_id")
            if migrated_chat_id:
                payload["chat_id"] = migrated_chat_id
                response = _http.post(f"{api_base}/sendMessage", json=payload, timeout=10).json()
            if response.get("ok"):
                result = response["result"]
                refs[key] = {
                    "chat_id": result.get("chat", {}).get("id", payload["chat_id"]),
                    "message_id": result["message_id"],
                }
                overall_success = True
            else:
                logger.error("Không thể gửi cảnh báo slot: %s", response.get("description"))
        except (requests.RequestException, ValueError, KeyError) as exc:
            logger.error("Gửi cảnh báo slot thất bại (%s).", type(exc).__name__)

    return refs, overall_success


def send_status_report(events: list) -> bool:
    """
    Gui bao cao dinh ky theo template gon gang, ro rang.
    Neu con cho = 0: hien '🔴 Còn chỗ: 0'
    Neu con cho > 0: hien '🔥 N hoạt động đang còn slot'
    """
    now_time = datetime.datetime.now().strftime("%H:%M • %d/%m/%Y")
    total = len(events)
    avail_count = sum(1 for e in events if e.get("is_available"))

    if avail_count == 0:
        summary_line = f"📋 <b>{total} hoạt động</b> | 🔴 <b>Còn chỗ: 0</b>"
    else:
        summary_line = f"📋 <b>{total} hoạt động</b> | 🔥 <b>{avail_count} hoạt động đang còn slot</b>"

    event_lines = []
    if events:
        for ev in events:
            t = html.escape(ev.get("title", ""))
            curr = ev.get("current_slots")
            tot = ev.get("max_slots")
            pts = html.escape(str(ev.get("points", "0")))
            dl = html.escape(str(ev.get("deadline", "")))

            # Dinh dang han gon vd 01-10-2026 -> 01/10
            dl_short = dl.replace("-", "/")
            if dl_short.count("/") == 2:
                dl_short = "/".join(dl_short.split("/")[:2])

            ratio = f"{curr}/{tot}" if curr is not None and tot is not None else ev.get("status_text", "")
            icon = "🟢" if ev.get("is_available") else "🔴"

            event_lines.append(
                f"{icon} <b>{ratio}</b> • {t}\n"
                f"   🏆 <b>+{pts}đ</b> • Hạn {dl_short}"
            )
        events_block = "\n\n".join(event_lines)
    else:
        events_block = "<i>Hiện tại không có sự kiện nào trong danh sách.</i>"

    # Tinh chu ky gio/phut cho tieu de
    if Config.STATUS_UPDATE_MINUTES >= 60 and Config.STATUS_UPDATE_MINUTES % 60 == 0:
        freq_str = f"({Config.STATUS_UPDATE_MINUTES // 60} tiếng / lần)"
    else:
        freq_str = f"({Config.STATUS_UPDATE_MINUTES} phút / lần)"

    # Dong Donate
    donate_line = ""
    if Config.DONATE_URL:
        donate_line = f"\n\n━━━━━━━━━━━━━━\n☕ <b>Ủng hộ :</b> <a href=\"{Config.DONATE_URL}\"><b>Donate</b></a>"

    msg = (
        f"📊 <b>IUH ĐRL — BÁO CÁO ĐỊNH KỲ</b> <i>{freq_str}</i>\n\n"
        f"⏰ {now_time}\n\n"
        f"🟢 Bot hoạt động bình thường • Quét mỗi {Config.CHECK_INTERVAL}s\n\n"
        f"{summary_line}\n\n"
        f"{events_block}\n\n"
        "🔔 <i>Bot sẽ báo ngay khi có hoạt động mới hoặc xuất hiện slot trống.</i>"
        f"{donate_line}"
    )

    # Báo cáo định kỳ dành cho nhóm người dùng.
    group_ids = [cid for cid in Config.TELEGRAM_CHAT_IDS if str(cid).startswith("-")]
    return send_telegram_message(
        msg,
        disable_preview=True,
        pin_if_group=False,
        target_chat_ids=group_ids,
        disable_notification=False,
    )


def send_session_expired_alert() -> bool:
    """
    Canh bao khi phien dang nhap (Cookie) bi het han.
    Chi gui rieng cho Quan tri vien (chat_id ca nhan), khong gui vao nhom chung.
    """
    now_str = datetime.datetime.now().strftime("%H:%M:%S - %d/%m/%Y")
    msg = (
        "⚠️⚠️⚠️ <b>CẢNH BÁO: COOKIE HẾT HẠN!</b> ⚠️⚠️⚠️\n\n"
        "Phiên đăng nhập trên cổng Đoàn Thanh niên IUH đã hết hạn.\n"
        f"⏰ Thời điểm phát hiện: <i>{now_str}</i>\n\n"
        "👉 <b>Cách khắc phục:</b>\n"
        "1. Mở trình duyệt vào lại: <a href=\"https://doantn.iuh.edu.vn/login.html\">doantn.iuh.edu.vn</a>\n"
        "2. Đăng nhập tài khoản sinh viên.\n"
        "3. Nhấn <code>F12</code> ➔ Chọn tab <b>Application</b> ➔ <b>Cookies</b> ➔ <code>doantn.iuh.edu.vn</code>\n"
        "4. Copy giá trị của <code>PHPSESSID</code>.\n"
        "5. Dán vào file <code>.env</code> và khởi động lại Tool."
    )
    play_alert_sound()

    # Loc chi gui den tai khoan ca nhan cua Admin (khong phai ID nhom co dau tru)
    admin_ids = [cid for cid in Config.TELEGRAM_CHAT_IDS if not str(cid).startswith("-")]
    if not admin_ids and Config.TELEGRAM_CHAT_IDS:
        admin_ids = [Config.TELEGRAM_CHAT_IDS[0]]

    return send_telegram_message(msg, target_chat_ids=admin_ids, pin_if_group=False)
