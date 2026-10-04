import json
import logging
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from config import Config
from logging_config import configure_logging

logger = logging.getLogger("health-watchdog")
HEALTH_STATE_FILE = Config.DATA_DIR / "health_status.json"
TIMEZONE = timezone(timedelta(hours=7))


def _main_service_active() -> bool:
    result = subprocess.run(
        ["systemctl", "is-active", "--quiet", "iuh-drl-bot.service"],
        check=False,
        timeout=10,
    )
    return result.returncode == 0


def _monitor_state_fresh() -> bool:
    try:
        age_seconds = time.time() - Config.STATE_FILE.stat().st_mtime
        return age_seconds <= max(90, Config.CHECK_INTERVAL * 4)
    except OSError:
        return False


def _load_message_ids() -> dict:
    try:
        return json.loads(HEALTH_STATE_FILE.read_text(encoding="utf-8")).get("message_ids", {})
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return {}


def _save_message_ids(message_ids: dict) -> None:
    Config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    temporary = Path(str(HEALTH_STATE_FILE) + ".tmp")
    temporary.write_text(
        json.dumps({"message_ids": message_ids}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(HEALTH_STATE_FILE)


def _status_text(online: bool) -> str:
    now = datetime.now(TIMEZONE).strftime("%H:%M:%S • %d/%m/%Y")
    if online:
        headline = "🟢 <b>BOT ĐANG HOẠT ĐỘNG</b>"
        detail = "Hệ thống và lượt quét IUH gần nhất đều bình thường."
    else:
        headline = "🔴 <b>BOT ĐANG GIÁN ĐOẠN</b>"
        detail = "Service hoặc lượt quét IUH đang gặp sự cố. Vui lòng kiểm tra VPS."
    return (
        f"{headline}\n\n"
        f"{detail}\n\n"
        f"🕒 Cập nhật: <code>{now}</code>\n"
        f"🔄 Chu kỳ quét IUH: <b>{Config.CHECK_INTERVAL} giây</b>\n\n"
        "<i>Tin nhắn này được tự động cập nhật; bạn có thể ghim để theo dõi.</i>"
    )


def update_private_status() -> bool:
    personal_ids = [cid for cid in Config.TELEGRAM_CHAT_IDS if not str(cid).startswith("-")]
    if not personal_ids or not Config.TELEGRAM_BOT_TOKEN:
        logger.error("Thiếu private chat ID hoặc Telegram token.")
        return False

    online = _main_service_active() and _monitor_state_fresh()
    text = _status_text(online)
    message_ids = _load_message_ids()
    api_base = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}"
    all_ok = True

    for chat_id in personal_ids:
        key = str(chat_id)
        message_id = message_ids.get(key)
        updated = False
        if message_id:
            try:
                response = requests.post(
                    f"{api_base}/editMessageText",
                    json={
                        "chat_id": chat_id,
                        "message_id": message_id,
                        "text": text,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": True,
                    },
                    timeout=10,
                ).json()
                updated = bool(response.get("ok"))
            except (requests.RequestException, ValueError):
                updated = False

        if not updated:
            try:
                response = requests.post(
                    f"{api_base}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": text,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": True,
                        "disable_notification": True,
                    },
                    timeout=10,
                ).json()
                if response.get("ok"):
                    message_ids[key] = response["result"]["message_id"]
                else:
                    all_ok = False
                    logger.error("Không thể tạo tin trạng thái riêng: %s", response.get("description"))
            except (requests.RequestException, ValueError, KeyError) as exc:
                all_ok = False
                logger.error("Cập nhật trạng thái riêng thất bại (%s).", type(exc).__name__)

    _save_message_ids(message_ids)
    logger.info("Đã cập nhật trạng thái riêng: %s", "ONLINE" if online else "OFFLINE")
    return all_ok


if __name__ == "__main__":
    configure_logging()
    raise SystemExit(0 if update_private_status() else 1)
