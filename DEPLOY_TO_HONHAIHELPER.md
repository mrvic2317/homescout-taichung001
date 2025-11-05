# 部署 VicBot 到 vicbot.honhaihelper.com

本指南將協助您將 VicBot 部署到自定義域名 `https://vicbot.honhaihelper.com`

## 🎯 部署方案選擇

由於您有自定義域名，推薦使用以下平台：

### 方案 A：Railway（推薦 ⭐⭐⭐⭐⭐）
- ✅ 免費額度（$5/月或500小時）
- ✅ 自動 HTTPS/SSL
- ✅ 簡單的自定義域名配置
- ✅ 自動部署（連接 GitHub）

### 方案 B：Render
- ✅ 免費方案
- ✅ 自動 HTTPS/SSL
- ✅ 支援自定義域名

### 方案 C：自有 VPS
- 如果 honhaihelper.com 已經運行在自己的 VPS 上

---

## 📋 準備工作

### 1. 準備必要資訊

收集以下資訊：

```bash
# Discord Bot Token
# 從 https://discord.com/developers/applications 獲取
DISCORD_TOKEN=你的_Token

# 生成 JWT 密鑰
python -c "import secrets; print(secrets.token_hex(32))"
# 複製輸出的密鑰
```

### 2. 推送代碼到 GitHub

```bash
# 初始化 Git（如果還沒有）
git init

# 添加 .gitignore
echo "vicbot.db
.env
.venv/
__pycache__/
*.pyc
data/" > .gitignore

# 提交代碼
git add .
git commit -m "feat: add web version with FastAPI"

# 創建 GitHub 倉庫並推送
# 在 GitHub 上創建新倉庫，然後：
git remote add origin https://github.com/你的用戶名/vicbot.git
git branch -M main
git push -u origin main
```

---

## 🚀 方案 A：部署到 Railway

### 步驟 1：創建 Railway 專案

1. **註冊/登入 Railway**
   - 訪問 https://railway.app
   - 使用 GitHub 登入

2. **創建新專案**
   - 點擊 "New Project"
   - 選擇 "Deploy from GitHub repo"
   - 選擇您的 VicBot 倉庫
   - 點擊 "Deploy Now"

### 步驟 2：設定環境變數

在 Railway 專案中：

1. 點擊專案 → "Variables"
2. 添加以下變數：

```
DISCORD_TOKEN=你的_Discord_Token
JWT_SECRET_KEY=生成的_JWT_密鑰
PORT=8000
PYTHON_VERSION=3.11
TIMEZONE=Asia/Taipei
FRONTEND_URL=https://vicbot.honhaihelper.com
```

可選變數：
```
REPORT_CHANNEL_ID=你的頻道ID
SYSTEM_LOG_CHANNEL_ID=系統日誌頻道ID
ERROR_LOG_CHANNEL_ID=錯誤日誌頻道ID
```

### 步驟 3：配置自定義域名

1. **在 Railway 中添加域名**
   - 點擊專案 → "Settings" → "Domains"
   - 點擊 "Custom Domain"
   - 輸入：`vicbot.honhaihelper.com`
   - Railway 會顯示一個 CNAME 目標（例如：`xxx.up.railway.app`）

2. **配置 DNS 記錄**

   到您的 DNS 管理面板（管理 honhaihelper.com 的地方）：

   添加 CNAME 記錄：
   ```
   類型：CNAME
   名稱：vicbot
   目標：Railway 提供的地址（例如：xxx.up.railway.app）
   TTL：3600（或自動）
   ```

   **或者使用 A 記錄**（如果不支援 CNAME）：
   ```
   類型：A
   名稱：vicbot
   IP：Railway 提供的 IP 地址
   TTL：3600
   ```

3. **等待 DNS 生效**
   - DNS 更新可能需要 5-60 分鐘
   - 使用以下命令檢查：
   ```bash
   nslookup vicbot.honhaihelper.com
   # 或
   dig vicbot.honhaihelper.com
   ```

4. **驗證 SSL 證書**
   - Railway 會自動配置 SSL 證書
   - 等待幾分鐘後訪問 `https://vicbot.honhaihelper.com`

### 步驟 4：創建管理員帳號

部署完成後，創建管理員帳號：

1. **方式 A：使用 Railway Shell**
   - Railway Dashboard → 專案 → "Shell" 標籤
   - 執行：
   ```bash
   python
   >>> import asyncio
   >>> from web_api.auth.users import create_user, init_users_table
   >>> from src.database import init_db
   >>> asyncio.run(init_db())
   >>> asyncio.run(init_users_table())
   >>> asyncio.run(create_user(
   ...     discord_id=你的Discord_ID,
   ...     username="admin",
   ...     guild_id=伺服器ID,
   ...     password="你的密碼",
   ...     role="admin"
   ... ))
   >>> exit()
   ```

2. **方式 B：使用 API**
   ```bash
   curl -X POST "https://vicbot.honhaihelper.com/api/auth/register" \
     -H "Content-Type: application/json" \
     -d '{
       "discord_id": 你的Discord_ID,
       "username": "admin",
       "guild_id": 伺服器ID,
       "password": "你的密碼",
       "role": "admin"
     }'
   ```

### 步驟 5：測試部署

1. **檢查健康狀態**
   ```bash
   curl https://vicbot.honhaihelper.com/health
   ```

   預期回應：
   ```json
   {
     "status": "healthy",
     "service": "VicBot Web API",
     "version": "1.0.0"
   }
   ```

2. **訪問網頁管理面板**
   - 打開 https://vicbot.honhaihelper.com
   - 使用 Discord ID 和密碼登入

3. **測試 Discord Bot**
   - 在 Discord 輸入：`!房價查詢 北屯區`
   - 確認 Bot 有回應

4. **查看 API 文檔**
   - 訪問 https://vicbot.honhaihelper.com/api/docs

---

## 🚀 方案 B：部署到 Render

### 步驟 1：創建 Render 服務

1. **註冊/登入 Render**
   - 訪問 https://render.com
   - 使用 GitHub 登入

2. **創建 Web Service**
   - Dashboard → "New" → "Web Service"
   - 連接您的 GitHub 倉庫
   - 選擇 VicBot 專案

3. **配置服務**
   - Name: `vicbot`
   - Environment: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python start.py`
   - Plan: 選擇 Free

### 步驟 2：設定環境變數

在 Render 專案設定中添加環境變數（同 Railway）

### 步驟 3：配置自定義域名

1. **在 Render 中添加域名**
   - 專案設定 → "Custom Domain"
   - 輸入：`vicbot.honhaihelper.com`

2. **配置 DNS**（同 Railway 步驟）

### 步驟 4-5：同 Railway

---

## 🚀 方案 C：部署到自有 VPS

如果 honhaihelper.com 已經在您的 VPS 上運行：

### 步驟 1：SSH 到服務器

```bash
ssh user@你的服務器IP
```

### 步驟 2：安裝依賴

```bash
# 更新系統
sudo apt update && sudo apt upgrade -y

# 安裝 Python 3.11
sudo apt install python3.11 python3.11-venv python3-pip -y

# 安裝 Nginx（如果還沒有）
sudo apt install nginx -y
```

### 步驟 3：部署應用

```bash
# 克隆代碼
cd /opt
sudo git clone https://github.com/你的用戶名/vicbot.git
cd vicbot

# 創建虛擬環境
python3.11 -m venv .venv
source .venv/bin/activate

# 安裝依賴
pip install -r requirements.txt

# 設定環境變數
sudo nano .env
# 貼上環境變數（同上）
```

### 步驟 4：配置 Systemd 服務

```bash
sudo nano /etc/systemd/system/vicbot.service
```

內容：
```ini
[Unit]
Description=VicBot Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/vicbot
Environment="PATH=/opt/vicbot/.venv/bin"
ExecStart=/opt/vicbot/.venv/bin/python /opt/vicbot/start.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

啟動服務：
```bash
sudo systemctl daemon-reload
sudo systemctl enable vicbot
sudo systemctl start vicbot
sudo systemctl status vicbot
```

### 步驟 5：配置 Nginx 反向代理

```bash
sudo nano /etc/nginx/sites-available/vicbot.honhaihelper.com
```

內容：
```nginx
server {
    listen 80;
    server_name vicbot.honhaihelper.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

啟用網站：
```bash
sudo ln -s /etc/nginx/sites-available/vicbot.honhaihelper.com /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 步驟 6：配置 SSL（Let's Encrypt）

```bash
# 安裝 Certbot
sudo apt install certbot python3-certbot-nginx -y

# 獲取 SSL 證書
sudo certbot --nginx -d vicbot.honhaihelper.com

# 選擇選項 2（自動重定向 HTTP 到 HTTPS）
```

Certbot 會自動更新 Nginx 配置並設置自動續期。

### 步驟 7：測試部署

同 Railway 步驟 5

---

## 🔧 DNS 配置檢查清單

確保您的 DNS 記錄正確：

### Cloudflare 範例
```
類型：CNAME
名稱：vicbot
目標：Railway/Render 提供的地址
代理狀態：已代理（橙色雲朵）
```

### 其他 DNS 提供商
- 確保 TTL 設置為 3600 或更低（便於快速更新）
- 如果使用 A 記錄，確保 IP 地址正確
- 等待 DNS 傳播（5-60 分鐘）

### 檢查 DNS 生效

```bash
# macOS/Linux
nslookup vicbot.honhaihelper.com
dig vicbot.honhaihelper.com

# Windows
nslookup vicbot.honhaihelper.com
```

---

## ✅ 部署後檢查清單

- [ ] 訪問 https://vicbot.honhaihelper.com（主頁）
- [ ] 訪問 https://vicbot.honhaihelper.com/health（健康檢查）
- [ ] 訪問 https://vicbot.honhaihelper.com/api/docs（API 文檔）
- [ ] SSL 證書有效（瀏覽器顯示鎖頭圖示）
- [ ] 創建管理員帳號並測試登入
- [ ] Discord Bot 在伺服器中正常運作
- [ ] 測試房價查詢功能
- [ ] 測試 Web 管理面板各項功能

---

## 🐛 常見問題排查

### 問題 1：DNS 未生效

**症狀**：無法訪問 vicbot.honhaihelper.com

**解決方案**：
```bash
# 清除本地 DNS 緩存
# macOS
sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder

# Windows
ipconfig /flushdns

# Linux
sudo systemd-resolve --flush-caches
```

### 問題 2：502 Bad Gateway

**症狀**：訪問網站顯示 502 錯誤

**解決方案**：
- 檢查應用是否正在運行
- Railway/Render：查看部署日誌
- VPS：`sudo systemctl status vicbot`

### 問題 3：SSL 證書錯誤

**症狀**：瀏覽器顯示不安全

**解決方案**：
- Railway/Render：等待 5-10 分鐘自動配置
- VPS：重新運行 `sudo certbot --nginx -d vicbot.honhaihelper.com`

### 問題 4：Discord Bot 無回應

**症狀**：Bot 在線但不回應指令

**解決方案**：
- 檢查 `DISCORD_TOKEN` 環境變數
- 確認 Bot 已加入伺服器
- 檢查 Bot 權限設置

---

## 📊 監控與維護

### 設置日誌監控

配置環境變數：
```
SYSTEM_LOG_CHANNEL_ID=系統日誌頻道ID
ERROR_LOG_CHANNEL_ID=錯誤日誌頻道ID
```

系統會自動將日誌發送到 Discord 頻道。

### 更新部署

#### Railway/Render
```bash
# 推送更新到 GitHub
git add .
git commit -m "update: description"
git push

# 平台會自動重新部署
```

#### VPS
```bash
# SSH 到服務器
cd /opt/vicbot
git pull
source .venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl restart vicbot
```

---

## 🎉 完成！

部署完成後，您的團隊可以：

1. **使用 Discord Bot**
   - 在 Discord 輸入指令操作

2. **使用 Web 管理面板**
   - 訪問 https://vicbot.honhaihelper.com
   - 使用視覺化界面管理

3. **邀請團隊成員**
   - 使用 API 或 Web 註冊功能

---

需要協助？參考 [WEB_DEPLOYMENT.md](WEB_DEPLOYMENT.md) 或在 GitHub 提出 Issue。
