#!/usr/bin/env bash
set -e

APP_DIR="/opt/iuh-drl-bot"
APP_USER="iuh-drl-bot"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$(id -u)" -ne 0 ]; then
  echo "Hãy chạy script bằng root: sudo bash deploy_vps.sh"
  exit 1
fi

apt update
DEBIAN_FRONTEND=noninteractive apt install -y python3 python3-pip python3-venv git curl

if ! id "$APP_USER" >/dev/null 2>&1; then
  useradd --system --home "$APP_DIR" --shell /usr/sbin/nologin "$APP_USER"
fi

mkdir -p "$APP_DIR" "$APP_DIR/data" "$APP_DIR/logs"
if [ "$SOURCE_DIR" != "$APP_DIR" ]; then
  tar --exclude='.env' --exclude='venv' --exclude='.venv' \
    --exclude='__pycache__' --exclude='data' --exclude='logs' \
    -C "$SOURCE_DIR" -cf - . | tar -C "$APP_DIR" -xf -
fi

python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/python" -m pip install --upgrade pip
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"

chown -R root:root "$APP_DIR"
chown -R "$APP_USER:$APP_USER" "$APP_DIR/data" "$APP_DIR/logs"
chmod 755 "$APP_DIR" "$APP_DIR/deploy_vps.sh" "$APP_DIR/update_bot.sh"
if [ -f "$APP_DIR/.env" ]; then
  chown "$APP_USER:$APP_USER" "$APP_DIR/.env"
  chmod 600 "$APP_DIR/.env"
else
  echo "Chưa có $APP_DIR/.env. Tạo từ .env.example và điền secret trực tiếp trên VPS."
fi

install -m 0644 "$APP_DIR/iuh-drl-bot.service" /etc/systemd/system/iuh-drl-bot.service
install -m 0644 "$APP_DIR/iuh-drl-health.service" /etc/systemd/system/iuh-drl-health.service
install -m 0644 "$APP_DIR/iuh-drl-health.timer" /etc/systemd/system/iuh-drl-health.timer
install -m 0644 "$APP_DIR/iuh-drl-discord.service" /etc/systemd/system/iuh-drl-discord.service
systemctl daemon-reload
echo "Cài đặt hoàn tất. Test thủ công trước, sau đó enable/start service theo DEPLOY_VPS.md."
