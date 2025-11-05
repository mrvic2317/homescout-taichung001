# VicBot 網頁版 - 部署與使用指南

## 📖 目錄

- [系統架構](#系統架構)
- [功能介紹](#功能介紹)
- [本地開發](#本地開發)
- [部署到雲端](#部署到雲端)
- [環境變數設定](#環境變數設定)
- [使用說明](#使用說明)
- [常見問題](#常見問題)

---

## 🏗️ 系�架構

VicBot 採用 **雙端協同運作** 架構：

```
┌──────────────────────────────────────────────┐
│         共享資料庫 (SQLite)                   │
│         vicbot.db (中央資料源)               │
└──────────────────────────────────────────────┘
           ↑                           ↑
           │                           │
    ┌─────┴──────────┐         ┌──────┴─────────┐
    │                │         │                │
    │ Discord Bot    │         │ Web API        │
    │  (bot.py)      │         │  (FastAPI)     │
    │                │         │                │
    │ • 指令操作     │         │ • REST API     │
    │ • 自動提醒     │         │ • JWT 認證     │
    │ • 背景排程     │         │ • 網頁界面     │
    └────────────────┘         └────────────────┘
```

### 技術棧

- **後端框架**: FastAPI (Web API) + discord.py (Bot)
- **資料庫**: SQLite (共享)
- **認證**: JWT (JSON Web Tokens)
- **前端**: HTML5 + Bootstrap 5 + Vanilla JavaScript
- **部署**: Railway / Render / Docker

---

## ✨ 功能介紹

### Discord Bot 功能
- ✅ 監控管理 (`!監控新增`, `!監控列表`, `!監控刪除`)
- ✅ 案件管理 (`!案件新增`, `!案件列表`, `!案件更新`)
- ✅ 客戶管理 (`!客戶新增`, `!客戶列表`, `!客戶跟進`)
- ✅ 看屋排程 (`!看屋排程`, `!看屋列表`)
- ✅ 房價查詢 (`!房價查詢 [區域]`)
- ✅ 自動提醒 (看屋前 90 分鐘)
- ✅ 週報推送 (每週一上午 10 點)

### Web 管理面板功能
- 📊 **儀表板**: 即時統計數據
- 👁️ **監控管理**: 可視化管理監控條件
- 💼 **案件管理**: 完整案件追蹤與更新
- 👥 **客戶管理**: 客戶資料與跟進記錄
- 📅 **看屋排程**: 行程管理與提醒
- 📈 **房價查詢**: 台中市實價登錄查詢
- 🔐 **JWT 認證**: 安全的用戶身份驗證

---

## 💻 本地開發

### 1. 環境需求

- Python 3.11+
- pip

### 2. 安裝依賴

```bash
# 創建虛擬環境
python -m venv .venv

# 啟動虛擬環境
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# 安裝依賴
pip install -r requirements.txt
```

### 3. 設定環境變數

創建 `.env` 文件：

```env
# Discord Bot
DISCORD_TOKEN=your_discord_token_here
REPORT_CHANNEL_ID=your_channel_id_here
TIMEZONE=Asia/Taipei

# Web API
JWT_SECRET_KEY=your_secret_key_here
PORT=8000
FRONTEND_URL=http://localhost:8000

# 資料庫
DATABASE_PATH=vicbot.db
```

### 4. 初始化資料庫並創建管理員帳號

```bash
# 啟動 Python 互動環境
python

# 執行以下代碼
>>> import asyncio
>>> from web_api.auth.users import init_users_table, create_user
>>> from src.database import init_db
>>>
>>> # 初始化資料庫
>>> asyncio.run(init_db())
>>> asyncio.run(init_users_table())
>>>
>>> # 創建管理員帳號
>>> asyncio.run(create_user(
...     discord_id=123456789,  # 你的 Discord ID
...     username="admin",
...     guild_id=987654321,    # 你的 Discord 伺服器 ID
...     password="your_password",
...     role="admin"
... ))
>>>
>>> exit()
```

### 5. 啟動應用

#### 方式 A：同時啟動 Bot 和 Web API（推薦）

```bash
python start.py
```

#### 方式 B：分別啟動

**終端 1 - Discord Bot**:
```bash
python bot.py
```

**終端 2 - Web API**:
```bash
python -m uvicorn web_api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 6. 訪問應用

- **網頁管理面板**: http://localhost:8000
- **API 文檔**: http://localhost:8000/api/docs
- **健康檢查**: http://localhost:8000/health

---

## ☁️ 部署到雲端

### 選項 1: Railway（推薦 ⭐⭐⭐⭐⭐）

#### 優點
- 免費額度（每月 $5 USD 或 500 小時）
- 自動 HTTPS
- 簡單易用
- 支援 PostgreSQL（可升級）

#### 部署步驟

1. **註冊 Railway**
   - 訪問 https://railway.app
   - 使用 GitHub 登入

2. **創建新專案**
   - 點擊 "New Project"
   - 選擇 "Deploy from GitHub repo"
   - 選擇你的 VicBot 倉庫

3. **設定環境變數**

   在 Railway 專案設定中添加：
   ```
   DISCORD_TOKEN=你的_Discord_Token
   JWT_SECRET_KEY=隨機生成的密鑰
   REPORT_CHANNEL_ID=頻道ID
   PORT=8000
   PYTHON_VERSION=3.11
   ```

4. **部署**
   - Railway 會自動檢測 `railway.json` 並部署
   - 部署完成後會獲得一個網址（例如：`https://vicbot.up.railway.app`）

5. **獲取 Discord ID**

   打開 Discord 開發者模式：
   - 設定 → 進階 → 開發者模式
   - 右鍵點擊自己的頭像 → 複製 ID

6. **創建管理員帳號**

   使用 Railway 的 Shell 功能：
   ```bash
   python
   >>> import asyncio
   >>> from web_api.auth.users import create_user
   >>> asyncio.run(create_user(
   ...     discord_id=你的Discord_ID,
   ...     username="admin",
   ...     guild_id=伺服器ID,
   ...     password="密碼",
   ...     role="admin"
   ... ))
   ```

---

### 選項 2: Render

#### 部署步驟

1. **註冊 Render**
   - 訪問 https://render.com
   - 使用 GitHub 登入

2. **創建 Web Service**
   - Dashboard → New → Web Service
   - 連接 GitHub 倉庫
   - 選擇 VicBot 專案

3. **設定**
   - Name: vicbot
   - Environment: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python start.py`

4. **環境變數**
   同 Railway 設定

5. **部署**
   - 點擊 "Create Web Service"
   - 等待部署完成

---

### 選項 3: Docker

#### 本地測試

```bash
# 構建映像
docker build -t vicbot .

# 運行容器
docker run -d \
  -p 8000:8000 \
  -e DISCORD_TOKEN=your_token \
  -e JWT_SECRET_KEY=your_secret \
  -v $(pwd)/vicbot.db:/app/vicbot.db \
  --name vicbot \
  vicbot
```

#### 部署到雲端

支援任何 Docker 平台：
- AWS ECS
- Google Cloud Run
- Azure Container Instances
- DigitalOcean App Platform

---

## 🔧 環境變數設定

### 必要變數

| 變數名稱 | 說明 | 範例 |
|---------|------|------|
| `DISCORD_TOKEN` | Discord Bot Token | `MTk3NjM5ODI4OTAy...` |
| `JWT_SECRET_KEY` | JWT 加密金鑰 | `openssl rand -hex 32` |

### 選用變數

| 變數名稱 | 說明 | 預設值 |
|---------|------|--------|
| `PORT` | Web API 端口 | `8000` |
| `TIMEZONE` | 時區 | `Asia/Taipei` |
| `REPORT_CHANNEL_ID` | 週報推送頻道 ID | 無 |
| `FRONTEND_URL` | 前端網址（CORS） | 無 |
| `DATABASE_PATH` | 資料庫路徑 | `vicbot.db` |

### 生成密鑰

```bash
# 使用 OpenSSL
openssl rand -hex 32

# 使用 Python
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 📱 使用說明

### 登入網頁管理面板

1. 訪問部署的網址（例如：`https://vicbot.up.railway.app`）
2. 使用 Discord ID 和密碼登入
3. 成功後會顯示儀表板

### 創建用戶帳號

**方式 A: 使用 API（推薦）**

```bash
curl -X POST "https://your-domain/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "discord_id": 123456789,
    "username": "user1",
    "guild_id": 987654321,
    "password": "password123",
    "role": "member"
  }'
```

**方式 B: 使用 Python**

```python
import asyncio
from web_api.auth.users import create_user

asyncio.run(create_user(
    discord_id=123456789,
    username="user1",
    guild_id=987654321,
    password="password123",
    role="member"
))
```

### 功能使用

#### 1. 監控管理
- 點擊「監控」頁面
- 點擊「新增監控」按鈕
- 填寫區域、價格範圍、坪數範圍
- 提交後系統會自動推送符合條件的房源

#### 2. 案件管理
- 點擊「案件」頁面
- 新增、查看、更新案件資訊
- 支援狀態追蹤（跟進中、已成交、已結案）

#### 3. 客戶管理
- 點擊「客戶」頁面
- 新增客戶資料（姓名、預算、偏好區域）
- 記錄跟進互動

#### 4. 看屋排程
- 點擊「看屋」頁面
- 新增看屋行程
- 系統會在看屋前 90 分鐘透過 Discord 提醒

#### 5. 房價查詢
- 點擊「房價」頁面
- 輸入區域（例如：北屯區、西屯區文心路）
- 查看實價登錄統計和建案分組

---

## 🔍 API 文檔

部署完成後，訪問 `/api/docs` 可查看完整的 Swagger API 文檔。

### 主要端點

#### 認證
- `POST /api/auth/login` - 用戶登入
- `POST /api/auth/register` - 註冊新用戶
- `GET /api/auth/me` - 獲取當前用戶

#### 監控
- `GET /api/monitoring` - 查詢監控列表
- `POST /api/monitoring` - 新增監控
- `DELETE /api/monitoring/{id}` - 刪除監控

#### 案件
- `GET /api/cases` - 查詢案件列表
- `POST /api/cases` - 新增案件
- `GET /api/cases/{id}` - 查詢案件詳情
- `PUT /api/cases/{id}` - 更新案件

#### 客戶
- `GET /api/clients` - 查詢客戶列表
- `POST /api/clients` - 新增客戶
- `POST /api/clients/{id}/followups` - 新增跟進記錄

#### 看屋
- `GET /api/viewings` - 查詢看屋列表
- `POST /api/viewings` - 新增看屋排程

#### 房價
- `POST /api/price/query` - 查詢房價統計

---

## ❓ 常見問題

### Q1: 如何獲取 Discord Token？

1. 訪問 https://discord.com/developers/applications
2. 創建新應用或選擇現有應用
3. 點擊 "Bot" → "Reset Token"
4. 複製 Token（只會顯示一次）

### Q2: 如何獲取 Discord ID 和伺服器 ID？

1. 開啟 Discord 開發者模式：設定 → 進階 → 開發者模式
2. **用戶 ID**: 右鍵點擊自己的頭像 → 複製 ID
3. **伺服器 ID**: 右鍵點擊伺服器圖示 → 複製 ID

### Q3: 登入失敗怎麼辦？

檢查：
- Discord ID 是否正確
- 密碼是否正確
- 資料庫中是否有該用戶（使用創建帳號腳本）

### Q4: Discord Bot 沒有回應？

檢查：
- `DISCORD_TOKEN` 是否正確
- Bot 是否已加入伺服器
- Bot 權限是否足夠（需要管理員權限）

### Q5: 如何備份資料？

```bash
# 本地環境
cp vicbot.db vicbot_backup.db

# Railway/Render
# 使用 Shell 功能下載資料庫文件
```

### Q6: 如何更新部署？

#### Railway/Render
- 推送代碼到 GitHub
- 自動觸發重新部署

#### Docker
```bash
docker pull your-image
docker stop vicbot
docker rm vicbot
docker run -d ... vicbot
```

### Q7: Web 面板和 Discord Bot 數據不同步？

確認：
- 兩者使用同一個資料庫文件
- 檢查 `DATABASE_PATH` 環境變數
- 重啟服務

### Q8: 如何自訂前端樣式？

編輯 `frontend/static/css/style.css` 文件。

### Q9: 支援哪些區域的房價查詢？

目前僅支援台中市各區（北屯區、西屯區、南屯區等）。

### Q10: 如何新增更多功能？

參考 API 路由結構：
1. 在 `web_api/routers/` 創建新路由
2. 在 `web_api/main.py` 註冊路由
3. 在前端 `frontend/` 添加對應界面

---

## 🛠️ 技術支援

- **GitHub Issues**: https://github.com/your-repo/issues
- **Discord**: 加入開發者伺服器

---

## 📄 授權

本專案使用 MIT 授權。

房價數據來源：內政部不動產成交案件實價登錄
依政府資料開放授權條款 (OGDL) 第1版公眾釋出

---

## 🎉 結語

恭喜！您已經成功部署 VicBot 網頁版。

現在您可以透過 Discord 指令和網頁管理面板雙端管理房仲業務了！

**下一步**:
- ✅ 邀請團隊成員註冊帳號
- ✅ 設定監控條件
- ✅ 開始管理案件和客戶
- ✅ 享受自動化帶來的效率提升！
