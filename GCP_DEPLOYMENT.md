# VicBot GCP Compute Engine 部署指南

本指南適用於已有 GCP VM 的用戶，將 VicBot 部署到現有的 Compute Engine 實例上。

## 📋 前置需求

- ✅ GCP Compute Engine VM（正在運行）
- ✅ 有 SSH 訪問權限
- ✅ DNS 已配置（honhaihelper.com 指向此 VM）
- ✅ Discord Bot Token
- ✅ GitHub 倉庫（VicBot 代碼）

---

## 🚀 快速部署（推薦）

### 步驟 1：準備代碼

在本地推送代碼到 GitHub：

```bash
cd /home/a757539610/homescout-taichung/homescout-taichung001

# 初始化 Git（如果還沒有）
git init
git add .
git commit -m "feat: add VicBot web version"

# 推送到 GitHub
git remote add origin https://github.com/你的用戶名/vicbot.git
git branch -M main
git push -u origin main
```

### 步驟 2：上傳部署腳本

將部署腳本上傳到 GCP VM：

```bash
# 方式 A：使用 gcloud 命令
gcloud compute scp deploy_gcp.sh 你的VM名稱:~/ --zone=asia-east1-b

# 方式 B：使用 SSH
scp deploy_gcp.sh user@你的VM_IP:~/
```

### 步驟 3：執行部署

SSH 到 GCP VM 並執行：

```bash
# SSH 連接
gcloud compute ssh 你的VM名稱 --zone=asia-east1-b

# 或使用標準 SSH
ssh user@你的VM_IP

# 執行部署腳本
sudo bash deploy_gcp.sh
```

腳本會詢問：
1. **GitHub 倉庫 URL**：輸入您的倉庫地址
2. **Discord Token**：貼上您的 Discord Bot Token
3. **是否配置 SSL**：建議選擇 `y`（需要 DNS 已生效）

### 步驟 4：創建管理員帳號

部署完成後：

```bash
cd /opt/vicbot
sudo -u vicbot .venv/bin/python setup_admin.py
```

按提示輸入：
- Discord ID
- 用戶名
- Discord 伺服器 ID
- 密碼

### 步驟 5：測試訪問

```bash
# 檢查服務狀態
sudo systemctl status vicbot

# 訪問網站
# https://vicbot.honhaihelper.com
```

---

## 📦 手動部署（進階）

如果自動腳本有問題，可以手動執行：

### 1. 更新系統並安裝依賴

```bash
sudo apt update && sudo apt upgrade -y

sudo apt install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    nginx \
    certbot \
    python3-certbot-nginx \
    git
```

### 2. 創建應用用戶

```bash
sudo useradd -r -m -s /bin/bash vicbot
```

### 3. 克隆代碼

```bash
sudo git clone https://github.com/你的用戶名/vicbot.git /opt/vicbot
sudo chown -R vicbot:vicbot /opt/vicbot
```

### 4. 設置 Python 環境

```bash
cd /opt/vicbot
sudo -u vicbot python3.11 -m venv .venv
sudo -u vicbot .venv/bin/pip install -r requirements.txt
```

### 5. 配置環境變數

```bash
sudo -u vicbot nano /opt/vicbot/.env
```

內容：
```env
DISCORD_TOKEN=你的_Discord_Token
JWT_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
PORT=8000
TIMEZONE=Asia/Taipei
FRONTEND_URL=https://vicbot.honhaihelper.com
```

### 6. 配置 Systemd 服務

```bash
sudo nano /etc/systemd/system/vicbot.service
```

內容：
```ini
[Unit]
Description=VicBot Discord Bot and Web API
After=network.target

[Service]
Type=simple
User=vicbot
Group=vicbot
WorkingDirectory=/opt/vicbot
Environment="PATH=/opt/vicbot/.venv/bin"
ExecStart=/opt/vicbot/.venv/bin/python /opt/vicbot/start.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/vicbot/output.log
StandardError=append:/var/log/vicbot/error.log

[Install]
WantedBy=multi-user.target
```

啟用服務：
```bash
sudo mkdir -p /var/log/vicbot
sudo chown vicbot:vicbot /var/log/vicbot
sudo systemctl daemon-reload
sudo systemctl enable vicbot
sudo systemctl start vicbot
```

### 7. 配置 Nginx

```bash
sudo nano /etc/nginx/sites-available/vicbot.honhaihelper.com
```

內容：
```nginx
server {
    listen 80;
    server_name vicbot.honhaihelper.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /opt/vicbot/frontend/static;
        expires 30d;
    }
}
```

啟用網站：
```bash
sudo ln -s /etc/nginx/sites-available/vicbot.honhaihelper.com /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 8. 配置 SSL

```bash
sudo certbot --nginx -d vicbot.honhaihelper.com
```

---

## 🔧 DNS 配置

在您的 DNS 管理面板（管理 honhaihelper.com 的地方）：

### 方式 A：A 記錄（推薦）

```
類型：A
名稱：vicbot
值：您的 GCP VM 外部 IP
TTL：3600
```

獲取 VM IP：
```bash
gcloud compute instances describe 你的VM名稱 --zone=asia-east1-b --format="get(networkInterfaces[0].accessConfigs[0].natIP)"
```

### 方式 B：CNAME 記錄

如果使用 Cloud Load Balancer：
```
類型：CNAME
名稱：vicbot
值：您的負載均衡器地址
```

### 驗證 DNS

```bash
nslookup vicbot.honhaihelper.com
# 或
dig vicbot.honhaihelper.com
```

---

## 🔍 GCP 防火牆規則

確保允許 HTTP/HTTPS 流量：

```bash
# 創建防火牆規則（如果還沒有）
gcloud compute firewall-rules create allow-http \
    --allow tcp:80 \
    --source-ranges 0.0.0.0/0 \
    --target-tags http-server

gcloud compute firewall-rules create allow-https \
    --allow tcp:443 \
    --source-ranges 0.0.0.0/0 \
    --target-tags https-server

# 為 VM 添加標籤
gcloud compute instances add-tags 你的VM名稱 \
    --tags http-server,https-server \
    --zone asia-east1-b
```

---

## 📊 監控與管理

### 查看服務狀態

```bash
# 服務狀態
sudo systemctl status vicbot

# 實時日誌
sudo journalctl -u vicbot -f

# 應用日誌
sudo tail -f /var/log/vicbot/output.log
sudo tail -f /var/log/vicbot/error.log
```

### 重啟服務

```bash
# 重啟 VicBot
sudo systemctl restart vicbot

# 重載 Nginx
sudo systemctl reload nginx
```

### 更新代碼

```bash
cd /opt/vicbot
sudo -u vicbot git pull
sudo -u vicbot .venv/bin/pip install -r requirements.txt --upgrade
sudo systemctl restart vicbot
```

### 備份資料

```bash
# 備份資料庫
sudo cp /opt/vicbot/vicbot.db /opt/vicbot/vicbot.db.backup.$(date +%Y%m%d)

# 備份環境變數
sudo cp /opt/vicbot/.env /opt/vicbot/.env.backup

# 自動備份（添加到 crontab）
sudo crontab -e
# 添加：每天凌晨 3 點備份
# 0 3 * * * cp /opt/vicbot/vicbot.db /opt/vicbot/backups/vicbot.db.$(date +\%Y\%m\%d)
```

---

## 🛠️ 常用指令速查

```bash
# 服務管理
sudo systemctl start vicbot       # 啟動
sudo systemctl stop vicbot        # 停止
sudo systemctl restart vicbot     # 重啟
sudo systemctl status vicbot      # 狀態

# 日誌查看
sudo journalctl -u vicbot -n 100  # 最近 100 行
sudo journalctl -u vicbot -f      # 實時日誌
sudo tail -f /var/log/vicbot/output.log  # 應用輸出

# Nginx
sudo nginx -t                     # 測試配置
sudo systemctl reload nginx       # 重載配置
sudo tail -f /var/log/nginx/vicbot.honhaihelper.com_access.log

# SSL 證書續期
sudo certbot renew               # 手動續期
sudo certbot certificates        # 查看證書
```

---

## ❓ 常見問題

### Q1: 服務啟動失敗

```bash
# 查看詳細錯誤
sudo journalctl -u vicbot -n 50 --no-pager

# 常見原因：
# 1. 環境變數錯誤 → 檢查 /opt/vicbot/.env
# 2. 端口被占用 → sudo lsof -i :8000
# 3. 權限問題 → sudo chown -R vicbot:vicbot /opt/vicbot
```

### Q2: SSL 證書配置失敗

```bash
# 確認 DNS 已生效
nslookup vicbot.honhaihelper.com

# 確認 Nginx 配置正確
sudo nginx -t

# 手動重試
sudo certbot --nginx -d vicbot.honhaihelper.com
```

### Q3: Discord Bot 無回應

```bash
# 檢查日誌
sudo tail -f /var/log/vicbot/output.log

# 確認 Token 正確
sudo -u vicbot cat /opt/vicbot/.env | grep DISCORD_TOKEN

# 重啟服務
sudo systemctl restart vicbot
```

### Q4: 502 Bad Gateway

```bash
# 確認應用正在運行
sudo systemctl status vicbot

# 確認端口監聽
sudo lsof -i :8000

# 檢查 Nginx 配置
sudo nginx -t

# 查看 Nginx 錯誤日誌
sudo tail -f /var/log/nginx/error.log
```

### Q5: 如何更改端口

編輯環境變數：
```bash
sudo -u vicbot nano /opt/vicbot/.env
# 修改 PORT=8000 為其他端口

# 同時修改 Nginx 配置
sudo nano /etc/nginx/sites-available/vicbot.honhaihelper.com
# 修改 proxy_pass http://127.0.0.1:新端口;

# 重啟服務
sudo systemctl restart vicbot
sudo systemctl reload nginx
```

---

## 🎉 完成清單

部署完成後，確認：

- [ ] 服務正常運行（`sudo systemctl status vicbot`）
- [ ] 訪問 https://vicbot.honhaihelper.com（顯示登入頁面）
- [ ] SSL 證書有效（瀏覽器顯示綠鎖）
- [ ] API 文檔可訪問（https://vicbot.honhaihelper.com/api/docs）
- [ ] 創建管理員帳號成功
- [ ] Discord Bot 在線並能回應指令
- [ ] Web 管理面板功能正常

---

## 📞 技術支援

遇到問題？
1. 查看本文檔的常見問題章節
2. 查看應用日誌：`sudo journalctl -u vicbot -n 100`
3. 參考 [WEB_DEPLOYMENT.md](WEB_DEPLOYMENT.md)
4. 在 GitHub 提交 Issue

---

**部署成功！** 🎊

您的團隊現在可以透過以下方式使用 VicBot：
- 🌐 Web 管理面板：https://vicbot.honhaihelper.com
- 🤖 Discord 指令：在伺服器中輸入 `!房價查詢 北屯區`
