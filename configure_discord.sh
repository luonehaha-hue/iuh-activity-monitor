#!/usr/bin/env bash
set -e

ENV_FILE="/opt/iuh-drl-bot/.env"

if [ "$(id -u)" -ne 0 ]; then
  echo "Hãy chạy bằng root: sudo bash /opt/iuh-drl-bot/configure_discord.sh"
  exit 1
fi

read -rsp "Dán Discord Bot Token (sẽ không hiển thị): " DISCORD_SETUP_TOKEN
echo
read -rp "Dán Discord Channel ID: " DISCORD_SETUP_CHANNEL

if [ -z "$DISCORD_SETUP_TOKEN" ] || ! [[ "$DISCORD_SETUP_CHANNEL" =~ ^[0-9]+$ ]]; then
  echo "Token trống hoặc Channel ID không hợp lệ."
  exit 1
fi

export DISCORD_SETUP_TOKEN DISCORD_SETUP_CHANNEL ENV_FILE
python3 - <<'PY'
import os
from pathlib import Path

path = Path(os.environ["ENV_FILE"])
values = {
    "DISCORD_BOT_TOKEN": os.environ["DISCORD_SETUP_TOKEN"],
    "DISCORD_CHANNEL_ID": os.environ["DISCORD_SETUP_CHANNEL"],
}
lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
output = []
seen = set()
for line in lines:
    key = line.split("=", 1)[0].strip() if "=" in line else ""
    if key in values:
        output.append(f"{key}={values[key]}")
        seen.add(key)
    else:
        output.append(line)
for key, value in values.items():
    if key not in seen:
        output.append(f"{key}={value}")
path.write_text("\n".join(output) + "\n", encoding="utf-8")
PY

unset DISCORD_SETUP_TOKEN DISCORD_SETUP_CHANNEL
chown iuh-drl-bot:iuh-drl-bot "$ENV_FILE"
chmod 600 "$ENV_FILE"
echo "Đã lưu Discord Token và Channel ID an toàn vào .env."
