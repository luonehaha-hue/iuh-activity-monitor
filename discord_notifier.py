import logging
from datetime import datetime

import requests

from config import Config

logger = logging.getLogger("discord")
_http = requests.Session()
API_BASE = "https://discord.com/api/v10"


def _enabled() -> bool:
    return bool(Config.DISCORD_BOT_TOKEN and Config.DISCORD_CHANNEL_ID)


def _headers() -> dict:
    return {
        "Authorization": f"Bot {Config.DISCORD_BOT_TOKEN}",
        "Content-Type": "application/json",
    }


def _slot_embed(event: dict, is_full: bool = False) -> dict:
    current = event.get("current_slots")
    maximum = event.get("max_slots")
    available = event.get("available_slots")
    if current is not None and maximum is not None:
        slot_text = f"{current} / {maximum} → " + ("ĐÃ HẾT CHỖ" if is_full else f"CÒN {available} CHỖ")
    else:
        slot_text = str(event.get("status_text", "Không rõ"))

    fields = [
        {"name": "👥 Số lượng", "value": slot_text, "inline": False},
        {"name": "🏆 Điểm", "value": f"+{event.get('points', '0')} điểm", "inline": True},
        {"name": "📅 Hạn đăng ký", "value": str(event.get("deadline", "Chưa rõ")), "inline": True},
    ]
    if event.get("location"):
        fields.append({"name": "📍 Địa điểm", "value": str(event["location"]), "inline": False})
    if event.get("event_time"):
        fields.append({"name": "🕔 Thời gian tổ chức", "value": str(event["event_time"]), "inline": False})

    return {
        "title": "🔴 SLOT ĐÃ HẾT" if is_full else "🔥 SLOT ĐRL VỪA MỞ",
        "description": f"**{event.get('title', 'Không rõ')}**",
        "color": 0xE74C3C if is_full else 0x2ECC71,
        "fields": fields,
        "url": event.get("register_url") or Config.URL_TRA_CUU,
        "footer": {"text": "IUH ĐRL • Dữ liệu cập nhật tự động"},
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


def _register_components(event: dict) -> list:
    """Build a visible Discord link button for the IUH registration page."""
    register_url = event.get("register_url") or Config.URL_TRA_CUU
    return [
        {
            "type": 1,
            "components": [
                {
                    "type": 2,
                    "style": 5,
                    "label": "Đăng ký ngay",
                    "emoji": {"name": "👉"},
                    "url": register_url,
                }
            ],
        }
    ]


def upsert_discord_slot_alert(
    event: dict,
    message_id: str = None,
    is_full: bool = False,
    create_if_missing: bool = True,
):
    if not _enabled():
        return message_id, False

    payload = {
        "content": "" if message_id or is_full else "@everyone",
        "embeds": [_slot_embed(event, is_full=is_full)],
        "components": _register_components(event),
        "allowed_mentions": {"parse": ["everyone"] if not message_id and not is_full else []},
    }
    try:
        if message_id:
            response = _http.patch(
                f"{API_BASE}/channels/{Config.DISCORD_CHANNEL_ID}/messages/{message_id}",
                headers=_headers(), json=payload, timeout=10,
            )
            if response.status_code == 200:
                return str(response.json()["id"]), True
            logger.warning("Discord không edit được tin cũ (HTTP %s).", response.status_code)

        if not create_if_missing:
            return message_id, False

        response = _http.post(
            f"{API_BASE}/channels/{Config.DISCORD_CHANNEL_ID}/messages",
            headers=_headers(), json=payload, timeout=10,
        )
        if response.status_code in (200, 201):
            return str(response.json()["id"]), True
        logger.error("Discord không gửi được cảnh báo (HTTP %s).", response.status_code)
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.error("Discord cảnh báo thất bại (%s).", type(exc).__name__)
    return message_id, False


def send_discord_status_report(events: list) -> bool:
    if not _enabled():
        return False
    available = [event for event in events if event.get("is_available")]
    lines = []
    for event in events:
        current = event.get("current_slots")
        maximum = event.get("max_slots")
        ratio = f"{current}/{maximum}" if current is not None and maximum is not None else event.get("status_text", "")
        icon = "🟢" if event.get("is_available") else "🔴"
        lines.append(f"{icon} **{ratio}** • {event.get('title', '')}\n🏆 +{event.get('points', '0')}đ • Hạn {event.get('deadline', '')}")
    extra_fields = [
        {
            "name": "🔔 Thông báo",
            "value": "*Bot sẽ báo ngay khi có hoạt động mới hoặc xuất hiện slot trống.*",
            "inline": False,
        }
    ]
    if Config.DONATE_URL:
        extra_fields.append(
            {
                "name": "☕ Ủng hộ",
                "value": f"[Donate]({Config.DONATE_URL})",
                "inline": False,
            }
        )

    embed = {
        "title": "📊 IUH ĐRL — BÁO CÁO ĐỊNH KỲ",
        "description": "\n\n".join(lines) if lines else "Hiện chưa có hoạt động.",
        "color": 0x2ECC71,
        "fields": [
            {"name": "Tổng quan", "value": f"{len(events)} hoạt động • {len(available)} hoạt động còn slot"},
            *extra_fields,
        ],
        "footer": {"text": f"Bot quét mỗi {Config.CHECK_INTERVAL}s • Báo cáo mỗi {Config.STATUS_UPDATE_MINUTES} phút"},
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    try:
        response = _http.post(
            f"{API_BASE}/channels/{Config.DISCORD_CHANNEL_ID}/messages",
            headers=_headers(), json={"embeds": [embed]}, timeout=10,
        )
        if response.status_code in (200, 201):
            return True
        logger.error("Discord không gửi được báo cáo (HTTP %s).", response.status_code)
    except requests.RequestException as exc:
        logger.error("Discord báo cáo thất bại (%s).", type(exc).__name__)
    return False
