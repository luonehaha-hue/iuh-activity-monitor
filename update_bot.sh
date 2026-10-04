#!/usr/bin/env bash
set -e

APP_DIR="/opt/iuh-drl-bot"
APP_USER="iuh-drl-bot"
BACKUP_DIR="/opt/iuh-drl-bot-backups"
STAMP="$(date +%Y%m%d-%H%M%S)"

if [ "$(id -u)" -ne 0 ]; then
  echo "Hãy chạy script bằng root: sudo bash update_bot.sh"
  exit 1
fi

cd "$APP_DIR"
mkdir -p "$BACKUP_DIR"
if [ -d data ] && [ "$(find data -mindepth 1 -print -quit)" ]; then
  tar -czf "$BACKUP_DIR/data-$STAMP.tar.gz" data
fi

if [ -d .git ]; then
  git pull --ff-only
else
  echo "Không có .git; bỏ qua git pull. Upload code mới (không ghi đè .env/data) rồi chạy lại."
fi

"$APP_DIR/venv/bin/pip" install -r requirements.txt
chown -R "$APP_USER:$APP_USER" "$APP_DIR/data" "$APP_DIR/logs"
if [ -f .env ]; then
  chown "$APP_USER:$APP_USER" .env
  chmod 600 .env
fi
install -m 0644 iuh-drl-bot.service /etc/systemd/system/iuh-drl-bot.service
install -m 0644 iuh-drl-health.service /etc/systemd/system/iuh-drl-health.service
install -m 0644 iuh-drl-health.timer /etc/systemd/system/iuh-drl-health.timer
install -m 0644 iuh-drl-discord.service /etc/systemd/system/iuh-drl-discord.service
systemctl daemon-reload
systemctl restart iuh-drl-bot
systemctl enable --now iuh-drl-health.timer
systemctl start iuh-drl-health.service
systemctl enable --now iuh-drl-discord
systemctl --no-pager --full status iuh-drl-bot
