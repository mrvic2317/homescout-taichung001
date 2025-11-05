# VicBot - 房仲管理系統

VicBot 是一個專為房仲團隊打造的**雙端管理系統**，提供 **Discord Bot** 和 **Web 管理面板** 兩種操作方式，協助管理房源監控、案件、客戶與看屋排程。

## 🌟 系統特色

- 🤖 **Discord Bot**：指令操作、自動提醒、週報推送
- 🌐 **Web 管理面板**：圖形化界面、數據視覺化、批量操作
- 🔄 **即時同步**：兩端共享資料庫，所有變更即時同步
- 🔐 **安全認證**：JWT 身份驗證、私訊保護

## 🚀 快速開始

### 方式 A：使用 Web 版本（推薦 ⭐）

```bash
# 1. 安裝依賴
pip install -r requirements.txt

# 2. 設定環境變數（創建 .env 文件）
DISCORD_TOKEN=你的_Discord_Token
JWT_SECRET_KEY=隨機密鑰

# 3. 創建管理員帳號
python setup_admin.py

# 4. 啟動系統（同時運行 Bot 和 Web API）
python start.py

# 5. 訪問網頁管理面板
# http://localhost:8000
```

### 方式 B：僅使用 Discord Bot

```bash
# 1. 安裝依賴
pip install -r requirements.txt

# 2. 設定環境變數
DISCORD_TOKEN=你的_Discord_Token

# 3. 啟動 Bot
python bot.py
```

## 📖 主要功能

### Discord Bot 指令

| 功能 | 指令 | 說明 |
|------|------|------|
| 監控管理 | `!監控新增`, `!監控列表`, `!監控刪除` | 房源監控條件管理 |
| 物件查詢 | `!物件查詢 [區域] [價格] [坪數]` | 快速查詢房源 |
| 案件管理 | `!案件新增`, `!案件列表`, `!案件更新` | 案件追蹤與管理 |
| 客戶管理 | `!客戶新增`, `!客戶列表`, `!客戶跟進` | 客戶資料與跟進 |
| 看屋排程 | `!看屋排程`, `!看屋列表` | 行程管理與提醒 |
| 房價查詢 | `!房價查詢 [區域]` | 台中市實價登錄查詢 |
| 市場行情 | `!行情 [區域]`, `!報表` | 行情統計與週報 |

### Web 管理面板功能

- 📊 **儀表板**：即時統計數據（監控數、案件數、客戶數、看屋數）
- 👁️ **監控管理**：可視化管理監控條件
- 💼 **案件管理**：完整案件追蹤與狀態更新
- 👥 **客戶管理**：客戶資料與跟進記錄
- 📅 **看屋排程**：行程管理與提醒設定
- 📈 **房價查詢**：實價登錄統計與建案分組

## 🔧 環境變數

### 必要變數

- `DISCORD_TOKEN`：Discord Bot Token（必填）
- `JWT_SECRET_KEY`：JWT 加密金鑰（Web 版必填）

### 選用變數

- `REPORT_CHANNEL_ID`：週報推送頻道 ID
- `TIMEZONE`：時區（預設 `Asia/Taipei`）
- `PORT`：Web API 端口（預設 `8000`）

## 📦 專案結構

```
vicbot/
├── bot.py                  # Discord Bot 主程式
├── start.py                # 整合啟動腳本
├── setup_admin.py          # 管理員帳號設置
├── src/                    # Bot 核心模組
│   ├── database.py         # 資料庫管理
│   ├── config.py           # 配置管理
│   └── services/           # 業務邏輯
├── web_api/                # Web API
│   ├── main.py             # FastAPI 主應用
│   ├── auth/               # 認證模組
│   ├── models/             # 數據模型
│   └── routers/            # API 路由
├── frontend/               # 前端
│   ├── templates/          # HTML 模板
│   └── static/             # 靜態資源
└── WEB_DEPLOYMENT.md       # 部署文檔
```

## 🌐 部署到雲端

支援多種部署平台：

- ✅ **Railway**（推薦）：免費額度、自動 HTTPS
- ✅ **Render**：免費方案、簡單易用
- ✅ **Docker**：支援任何 Docker 平台
- ✅ **Heroku**、**AWS**、**GCP** 等

詳細部署指南請參考：[WEB_DEPLOYMENT.md](WEB_DEPLOYMENT.md)

## 📚 文檔

- [Web 部署與使用指南](WEB_DEPLOYMENT.md)
- [API 文檔](http://localhost:8000/api/docs)（啟動後訪問）

## 🛠️ 技術棧

- **後端**: FastAPI、discord.py、SQLite
- **前端**: HTML5、Bootstrap 5、Vanilla JavaScript
- **認證**: JWT (JSON Web Tokens)
- **部署**: Railway / Render / Docker

## 📄 授權與數據來源

- 程式授權：MIT License
- 房價數據來源：內政部不動產成交案件實價登錄
- 依政府資料開放授權條款 (OGDL) 第1版公眾釋出

## 🎯 下一步

1. ✅ 部署到雲端（參考 [WEB_DEPLOYMENT.md](WEB_DEPLOYMENT.md)）
2. ✅ 邀請團隊成員註冊帳號
3. ✅ 設定監控條件
4. ✅ 開始管理案件和客戶
5. ✅ 享受自動化帶來的效率提升！

## 💡 常見問題

### 如何獲取 Discord Token？

1. 訪問 https://discord.com/developers/applications
2. 創建新應用或選擇現有應用
3. 點擊 "Bot" → "Reset Token"
4. 複製 Token（只會顯示一次）

### 如何獲取 Discord ID？

1. 開啟 Discord 開發者模式：設定 → 進階 → 開發者模式
2. 右鍵點擊自己的頭像 → 複製 ID

更多問題請參考 [WEB_DEPLOYMENT.md](WEB_DEPLOYMENT.md#常見問題)

---

**開發者**: VicBot Team
**版本**: 1.0.0（支援 Discord Bot + Web 管理面板）
