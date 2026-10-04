# Deploy bot IUH ĐRL lên Ubuntu 24.04

Không gửi password, private key, Telegram token hoặc cookie IUH vào chat. Nhập password SSH trực tiếp trong terminal. Tất cả secret chỉ đặt trong `/opt/iuh-drl-bot/.env`.

## 1. Kết nối VPS

Từ PowerShell trên Windows:

```powershell
ssh root@180.93.115.215
```

## 2A. Đưa code lên bằng GitHub

Trên VPS (thay URL bằng repository của bạn):

```bash
apt update
apt install -y git
git clone https://github.com/USERNAME/REPOSITORY.git /tmp/iuh-drl-bot-source
cd /tmp/iuh-drl-bot-source
bash deploy_vps.sh
```

Repository phải là private nếu mã nguồn có thông tin riêng; `.env` không được commit.

## 2B. Đưa code lên bằng SCP từ Windows

Để chắc chắn không upload `.env`, tạo bản staging trong PowerShell:

```powershell
$src = 'D:\TestTool\Diemrenluyen'
$stage = "$env:TEMP\iuh-drl-bot-upload"
Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $stage | Out-Null
Get-ChildItem -LiteralPath $src -Force | Where-Object { $_.Name -notin @('.env', '.git', 'venv', '.venv', '__pycache__', 'data', 'logs') } | Copy-Item -Destination $stage -Recurse -Force
ssh root@180.93.115.215 "mkdir -p /tmp/iuh-drl-bot-source"
scp -r "$stage\*" root@180.93.115.215:/tmp/iuh-drl-bot-source/
ssh root@180.93.115.215
```

Sau khi nhập password trực tiếp trong terminal, chạy trên VPS:

```bash
cd /tmp/iuh-drl-bot-source
bash deploy_vps.sh
```

## 3. Tạo `.env` trực tiếp trên VPS

```bash
cp /opt/iuh-drl-bot/.env.example /opt/iuh-drl-bot/.env
nano /opt/iuh-drl-bot/.env
chown iuh-drl-bot:iuh-drl-bot /opt/iuh-drl-bot/.env
chmod 600 /opt/iuh-drl-bot/.env
```

Điền giá trị thật ngay trong `nano`, lưu bằng `Ctrl+O`, Enter và thoát bằng `Ctrl+X`. Không dán secret vào chat hay commit Git.

## 4. Test thủ công

```bash
sudo -u iuh-drl-bot /opt/iuh-drl-bot/venv/bin/python3 /opt/iuh-drl-bot/test_parser.py
sudo -u iuh-drl-bot /opt/iuh-drl-bot/venv/bin/python3 /opt/iuh-drl-bot/test_connection.py
sudo -u iuh-drl-bot /opt/iuh-drl-bot/venv/bin/python3 /opt/iuh-drl-bot/main.py
```

Sau khi thấy bot chạy đúng, nhấn `Ctrl+C`.

## 5. Bật systemd 24/7

```bash
systemctl daemon-reload
systemctl enable iuh-drl-bot
systemctl restart iuh-drl-bot
systemctl status iuh-drl-bot --no-pager
journalctl -u iuh-drl-bot -f
```

## 6. Kiểm tra sau deploy/reboot

```bash
systemd-analyze verify /etc/systemd/system/iuh-drl-bot.service
systemctl is-enabled iuh-drl-bot
systemctl is-active iuh-drl-bot
journalctl -u iuh-drl-bot -n 100 --no-pager
ls -l /opt/iuh-drl-bot/data/monitor_state.json
stat -c '%a %U:%G %n' /opt/iuh-drl-bot/.env
```

Để xác nhận tự khởi động sau reboot, chạy `reboot`, SSH lại, rồi:

```bash
systemctl status iuh-drl-bot --no-pager
journalctl -u iuh-drl-bot -n 100 --no-pager
```

## 7. Cập nhật bot sau này

Nếu deploy bằng Git:

```bash
cd /opt/iuh-drl-bot
sudo bash update_bot.sh
```

Nếu không dùng Git, upload code mới vào `/opt/iuh-drl-bot` nhưng không ghi đè `.env` hoặc `data/`, rồi chạy cùng lệnh trên.
