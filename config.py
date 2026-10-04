import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"
DATA_DIR = BASE_DIR / "data"
STATE_FILE = DATA_DIR / "monitor_state.json"

load_dotenv(dotenv_path=ENV_FILE, override=True)

class Config:
    BASE_DIR = BASE_DIR
    DATA_DIR = DATA_DIR
    STATE_FILE = STATE_FILE
    URL_TRA_CUU = "https://doantn.iuh.edu.vn/doanvien.html@211@Tra-cuu"
    URL_LOGIN = "https://doantn.iuh.edu.vn/login.html"

    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip().strip("\"'")
    raw_chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip().strip("\"'")

    # Cho phep dien nhieu chat_id cach nhau boi dau phay (vd: 6361097282, -100123456789)
    TELEGRAM_CHAT_IDS = [cid.strip() for cid in raw_chat_id.split(",") if cid.strip()]
    TELEGRAM_CHAT_ID = TELEGRAM_CHAT_IDS[0] if TELEGRAM_CHAT_IDS else ""

    DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "").strip().strip("\"'")
    DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID", "").strip().strip("\"'")

    raw_cookie = os.getenv("PHPSESSID", "").strip().strip("\"'")
    if "PHPSESSID=" in raw_cookie:
        PHPSESSID = raw_cookie.split("PHPSESSID=")[1].split(";")[0].strip()
    else:
        PHPSESSID = raw_cookie

    try:
        CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL_SECONDS", "20"))
    except ValueError:
        CHECK_INTERVAL = 20
    CHECK_INTERVAL = max(1, CHECK_INTERVAL)

    try:
        STATUS_UPDATE_MINUTES = int(os.getenv("STATUS_UPDATE_MINUTES", "60"))
    except ValueError:
        STATUS_UPDATE_MINUTES = 60
    STATUS_UPDATE_MINUTES = max(1, STATUS_UPDATE_MINUTES)

    try:
        NOTIFY_COOLDOWN_MINUTES = int(os.getenv("NOTIFY_COOLDOWN_MINUTES", "5"))
    except ValueError:
        NOTIFY_COOLDOWN_MINUTES = 5
    NOTIFY_COOLDOWN_MINUTES = max(0, NOTIFY_COOLDOWN_MINUTES)

    SOUND_ALERT = os.getenv("SOUND_ALERT", "True").strip().lower() in ("true", "1", "yes", "on")
    PIN_ALERT_IN_GROUP = os.getenv("PIN_ALERT_IN_GROUP", "False").strip().lower() in ("true", "1", "yes", "on")
    TAG_ALL_IN_GROUP = os.getenv("TAG_ALL_IN_GROUP", "True").strip().lower() in ("true", "1", "yes", "on")
    DONATE_URL = os.getenv("DONATE_URL", "").strip()

    @classmethod
    def reload(cls):
        load_dotenv(dotenv_path=ENV_FILE, override=True)
        cls.TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip().strip("\"'")
        raw_cid = os.getenv("TELEGRAM_CHAT_ID", "").strip().strip("\"'")
        cls.TELEGRAM_CHAT_IDS = [cid.strip() for cid in raw_cid.split(",") if cid.strip()]
        cls.TELEGRAM_CHAT_ID = cls.TELEGRAM_CHAT_IDS[0] if cls.TELEGRAM_CHAT_IDS else ""
        raw = os.getenv("PHPSESSID", "").strip().strip("\"'")
        if "PHPSESSID=" in raw:
            cls.PHPSESSID = raw.split("PHPSESSID=")[1].split(";")[0].strip()
        else:
            cls.PHPSESSID = raw
        cls.DONATE_URL = os.getenv("DONATE_URL", "").strip()
