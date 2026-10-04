import json
import logging
import time
from pathlib import Path

import requests
import urllib3

from config import Config
from discord_notifier import send_discord_status_report, upsert_discord_slot_alert
from parser import parse_events
from telegram_bot import send_session_expired_alert, send_status_report, upsert_slot_alert

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger("monitor")


class DRLMonitor:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://doantn.iuh.edu.vn/home.html",
            "Connection": "keep-alive",
        })
        self.notified_events = {}
        self.alert_messages = {}
        self.discord_alert_messages = {}
        self.last_status_report_time = time.time()
        self.session_expired_alerted = False
        self.previous_events = []
        self._load_state()

    def _load_state(self):
        try:
            if Config.STATE_FILE.exists():
                state = json.loads(Config.STATE_FILE.read_text(encoding="utf-8"))
                self.notified_events = state.get("notified_events", {})
                self.alert_messages = state.get("alert_messages", {})
                self.discord_alert_messages = state.get("discord_alert_messages", {})
                self.last_status_report_time = float(
                    state.get("last_status_report_time", self.last_status_report_time)
                )
                self.session_expired_alerted = bool(state.get("session_expired_alerted", False))
                logger.info("Đã nạp state từ %s", Config.STATE_FILE)
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            logger.warning("Không thể nạp state (%s); bot dùng state mới.", type(exc).__name__)

    def _save_state(self):
        Config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        state = {
            "notified_events": self.notified_events,
            "alert_messages": self.alert_messages,
            "discord_alert_messages": self.discord_alert_messages,
            "last_status_report_time": self.last_status_report_time,
            "session_expired_alerted": self.session_expired_alerted,
        }
        temp_path = Path(str(Config.STATE_FILE) + ".tmp")
        try:
            temp_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
            temp_path.replace(Config.STATE_FILE)
        except OSError as exc:
            logger.error("Không thể lưu state (%s).", type(exc).__name__)

    @staticmethod
    def get_event_key(event: dict) -> str:
        return f"{event.get('title')}_{event.get('semester')}"

    def _upsert_slot_alert_to_groups(
        self, event: dict, event_key: str, is_full: bool = False, create_if_missing: bool = True
    ):
        group_ids = [
            cid for cid in Config.TELEGRAM_CHAT_IDS if str(cid).startswith("-")
        ]
        if group_ids:
            refs, success = upsert_slot_alert(
                event,
                target_chat_ids=group_ids,
                message_refs=self.alert_messages.get(event_key, {}),
                is_full=is_full,
                create_if_missing=create_if_missing,
            )
            if refs:
                self.alert_messages[event_key] = refs
            discord_message_id, discord_success = upsert_discord_slot_alert(
                event,
                message_id=self.discord_alert_messages.get(event_key),
                is_full=is_full,
                create_if_missing=create_if_missing,
            )
            if discord_message_id:
                self.discord_alert_messages[event_key] = discord_message_id
            return success or discord_success
        else:
            logger.error("Không có Telegram group chat ID để gửi cảnh báo slot.")
            return False

    def _get_iuh_with_retry(self):
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                response = self.session.get(
                    Config.URL_TRA_CUU,
                    timeout=15,
                    verify=False,
                    allow_redirects=True,
                )
                if response.status_code < 500 and response.status_code != 429:
                    return response
                logger.warning("IUH HTTP %s (lần %s/%s).", response.status_code, attempt, max_attempts)
            except requests.exceptions.RequestException as exc:
                logger.warning(
                    "Request IUH lỗi %s (lần %s/%s).",
                    type(exc).__name__, attempt, max_attempts,
                )
            if attempt < max_attempts:
                time.sleep(2 ** (attempt - 1))
        return None

    def check_once(self):
        if Config.PHPSESSID:
            self.session.cookies.set("PHPSESSID", Config.PHPSESSID, domain="doantn.iuh.edu.vn")

        response = self._get_iuh_with_retry()
        if response is None:
            logger.error("Không thể kết nối IUH sau 3 lần thử.")
            return

        logger.info("IUH check: HTTP %s", response.status_code)
        if response.status_code != 200:
            logger.warning("IUH trả HTTP %s; bỏ qua lượt quét.", response.status_code)
            return

        success, events, message = parse_events(
            response.text, base_url=Config.URL_TRA_CUU, current_url=response.url
        )
        if not success:
            logger.error("%s", message)
            if not self.session_expired_alerted:
                send_session_expired_alert()
                self.session_expired_alerted = True
                self._save_state()
            return

        if "Không tìm thấy bảng" in message or "không có dòng" in message:
            logger.warning("Parser: %s", message)

        if self.session_expired_alerted:
            logger.info("Phiên đăng nhập IUH đã hợp lệ trở lại.")
            self.session_expired_alerted = False

        self.previous_events = events
        available_events = [event for event in events if event.get("is_available")]
        logger.info(
            "IUH check hoàn tất: HTTP %s | %s hoạt động | %s còn slot",
            response.status_code, len(events), len(available_events),
        )

        current_time = time.time()
        for event in available_events:
            event_key = self.get_event_key(event)
            available_slots = event.get("available_slots")
            last_info = self.notified_events.get(event_key)
            if last_info is None:
                logger.info("Phát hiện hoạt động còn slot: %s (%s chỗ)", event.get("title"), available_slots)
                self._upsert_slot_alert_to_groups(event, event_key)
                self.notified_events[event_key] = {
                    "last_time": current_time,
                    "last_avail": available_slots,
                }
            elif last_info.get("last_avail") != available_slots:
                logger.info(
                    "Cập nhật tin cảnh báo: %s (%s → %s chỗ)",
                    event.get("title"), last_info.get("last_avail"), available_slots,
                )
                self._upsert_slot_alert_to_groups(event, event_key)
                self.notified_events[event_key] = {
                    "last_time": current_time,
                    "last_avail": available_slots,
                }

        for event in events:
            if not event.get("is_available"):
                event_key = self.get_event_key(event)
                if event_key in self.notified_events:
                    logger.info("Hoạt động đã hết slot; cập nhật tin cũ: %s", event.get("title"))
                    self._upsert_slot_alert_to_groups(
                        event, event_key, is_full=True, create_if_missing=False
                    )
                self.notified_events.pop(event_key, None)
                self.alert_messages.pop(event_key, None)
                self.discord_alert_messages.pop(event_key, None)

        # Không giữ cache vô hạn cho các hoạt động đã biến mất khỏi trang.
        current_event_keys = {self.get_event_key(event) for event in events}
        for cached_key in list(self.notified_events):
            if cached_key not in current_event_keys:
                self.notified_events.pop(cached_key, None)
                self.alert_messages.pop(cached_key, None)
                self.discord_alert_messages.pop(cached_key, None)

        status_interval_sec = Config.STATUS_UPDATE_MINUTES * 60
        if current_time - self.last_status_report_time >= status_interval_sec:
            logger.info("Gửi báo cáo định kỳ qua Telegram.")
            send_status_report(events)
            send_discord_status_report(events)
            self.last_status_report_time = current_time
        self._save_state()

    def run_forever(self):
        Config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        logger.info("Bot started")
        logger.info(
            "Cấu hình: quét mỗi %s giây; báo cáo mỗi %s phút; âm thanh=%s",
            Config.CHECK_INTERVAL, Config.STATUS_UPDATE_MINUTES, Config.SOUND_ALERT,
        )
        self.check_once()
        if self.previous_events:
            logger.info("Gửi báo cáo ban đầu qua Telegram.")
            send_status_report(self.previous_events)
            send_discord_status_report(self.previous_events)

        while True:
            try:
                time.sleep(Config.CHECK_INTERVAL)
                self.check_once()
            except KeyboardInterrupt:
                logger.info("Bot stopped by user")
                break
            except Exception as exc:
                logger.exception("Ngoại lệ không mong muốn (%s); thử lại sau 5 giây.", type(exc).__name__)
                time.sleep(5)
