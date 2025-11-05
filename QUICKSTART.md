# VicBot 快速開始指南

## 🎯 5 分鐘快速上手

### 步驟 1：安裝依賴

```bash
pip install -r requirements.txt
```

### 步驟 2：設定環境變數

創建 `.env` 文件：

```env
DISCORD_TOKEN=你的_Discord_Token
JWT_SECRET_KEY=請使用下方指令生成
```

**生成 JWT 密鑰**：
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 步驟 3：創建管理員帳號

```bash
python setup_admin.py
```

按提示輸入：
- Discord ID（右鍵點擊自己頭像 → 複製 ID）
- 用戶名稱
- Discord 伺服器 ID（右鍵點擊伺服器圖示 → 複製 ID）
- 密碼

### 步驟 4：啟動系統

```bash
python start.py
```

看到以下訊息表示成功：
```
✅ Discord Bot 和 Web API 已啟動
📊 儀表板：http://localhost:8000
📖 API 文檔：http://localhost:8000/api/docs
```

### 步驟 5：登入網頁

1. 訪問 http://localhost:8000
2. 使用 Discord ID 和密碼登入
3. 開始使用！

---

## 🚀 測試功能

### 測試 Discord Bot

在 Discord 伺服器輸入：
```
!房價查詢 北屯區
```

### 測試 Web API

訪問 http://localhost:8000/api/docs 查看 API 文檔

### 測試網頁管理面板

1. 登入後查看儀表板
2. 點擊「監控」→ 「新增監控」
3. 填寫資料並提交
4. 回到儀表板查看統計數字更新

---

## ❓ 遇到問題？

### 問題：無法啟動

**解決方案**：
```bash
# 檢查 Python 版本（需要 3.11+）
python --version

# 重新安裝依賴
pip install -r requirements.txt --upgrade
```

### 問題：登入失敗

**解決方案**：
1. 確認 Discord ID 正確
2. 重新運行 `python setup_admin.py`
3. 檢查密碼是否正確

### 問題：Discord Bot 無回應

**解決方案**：
1. 確認 `DISCORD_TOKEN` 設定正確
2. 確認 Bot 已加入伺服器
3. 確認 Bot 有足夠權限

---

## 📚 下一步

- 📖 閱讀[完整部署指南](WEB_DEPLOYMENT.md)
- 🌐 部署到雲端（Railway / Render）
- 👥 邀請團隊成員註冊帳號
- 🎨 自訂前端樣式

---

## 💡 小技巧

### 僅啟動 Discord Bot

```bash
python bot.py
```

### 僅啟動 Web API

```bash
python -m uvicorn web_api.main:app --reload
```

### 創建普通用戶帳號

使用 API 文檔（http://localhost:8000/api/docs）：
1. 找到 `/api/auth/register`
2. 點擊 "Try it out"
3. 填寫資料並執行

---

**需要幫助？** 查看 [WEB_DEPLOYMENT.md](WEB_DEPLOYMENT.md#常見問題)
