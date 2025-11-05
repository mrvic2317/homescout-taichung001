#!/bin/bash
#
# VicBot GCP Compute Engine 一鍵部署腳本
# 用途：在現有 GCP VM 上部署 VicBot（Discord Bot + Web API）
#

set -e  # 遇到錯誤立即停止

echo "=================================================="
echo "🚀 VicBot GCP 部署腳本"
echo "=================================================="
echo ""

# 顏色輸出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 檢查是否為 root 或有 sudo 權限
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}❌ 此腳本需要 root 權限，請使用 sudo 執行${NC}"
   echo "用法: sudo bash deploy_gcp.sh"
   exit 1
fi

# ============ 配置變數 ============
APP_DIR="/opt/vicbot"
APP_USER="vicbot"
DOMAIN="vicbot.honhaihelper.com"

echo -e "${GREEN}📋 部署配置${NC}"
echo "  應用目錄: $APP_DIR"
echo "  運行用戶: $APP_USER"
echo "  域名: $DOMAIN"
echo ""

# ============ 1. 更新系統 ============
echo -e "${GREEN}1️⃣  更新系統套件...${NC}"
apt update -qq
apt upgrade -y -qq
echo -e "${GREEN}✅ 系統更新完成${NC}"
echo ""

# ============ 2. 安裝依賴 ============
echo -e "${GREEN}2️⃣  安裝依賴套件...${NC}"
apt install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    nginx \
    certbot \
    python3-certbot-nginx \
    git \
    curl \
    wget \
    -qq

echo -e "${GREEN}✅ 依賴安裝完成${NC}"
echo ""

# ============ 3. 創建應用用戶 ============
echo -e "${GREEN}3️⃣  創建應用用戶...${NC}"
if id "$APP_USER" &>/dev/null; then
    echo "用戶 $APP_USER 已存在，跳過"
else
    useradd -r -m -s /bin/bash $APP_USER
    echo -e "${GREEN}✅ 用戶 $APP_USER 已創建${NC}"
fi
echo ""

# ============ 4. 克隆/更新代碼 ============
echo -e "${GREEN}4️⃣  部署應用代碼...${NC}"

if [ -d "$APP_DIR" ]; then
    echo "應用目錄已存在，更新代碼..."
    cd $APP_DIR
    sudo -u $APP_USER git pull
else
    echo "克隆 GitHub 倉庫..."
    read -p "請輸入 GitHub 倉庫 URL: " REPO_URL
    git clone $REPO_URL $APP_DIR
    chown -R $APP_USER:$APP_USER $APP_DIR
fi

cd $APP_DIR
echo -e "${GREEN}✅ 代碼部署完成${NC}"
echo ""

# ============ 5. 設置 Python 虛擬環境 ============
echo -e "${GREEN}5️⃣  設置 Python 環境...${NC}"
if [ ! -d "$APP_DIR/.venv" ]; then
    sudo -u $APP_USER python3.11 -m venv $APP_DIR/.venv
fi

sudo -u $APP_USER $APP_DIR/.venv/bin/pip install --upgrade pip -q
sudo -u $APP_USER $APP_DIR/.venv/bin/pip install -r $APP_DIR/requirements.txt -q

echo -e "${GREEN}✅ Python 環境設置完成${NC}"
echo ""

# ============ 6. 配置環境變數 ============
echo -e "${GREEN}6️⃣  配置環境變數...${NC}"

if [ ! -f "$APP_DIR/.env" ]; then
    echo "創建 .env 文件..."

    # 提示用戶輸入
    read -p "請輸入 Discord Token: " DISCORD_TOKEN

    # 生成 JWT 密鑰
    JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")

    # 創建 .env 文件
    cat > $APP_DIR/.env <<EOF
# Discord Bot 設定
DISCORD_TOKEN=$DISCORD_TOKEN
TIMEZONE=Asia/Taipei

# Web API 設定
JWT_SECRET_KEY=$JWT_SECRET
PORT=8000
FRONTEND_URL=https://$DOMAIN

# 可選設定
# REPORT_CHANNEL_ID=
# SYSTEM_LOG_CHANNEL_ID=
# ERROR_LOG_CHANNEL_ID=
EOF

    chown $APP_USER:$APP_USER $APP_DIR/.env
    chmod 600 $APP_DIR/.env

    echo -e "${GREEN}✅ 環境變數已配置${NC}"
    echo -e "${YELLOW}JWT 密鑰: $JWT_SECRET${NC}"
    echo -e "${YELLOW}請妥善保存此密鑰！${NC}"
else
    echo ".env 文件已存在，跳過"
fi
echo ""

# ============ 7. 配置 Systemd 服務 ============
echo -e "${GREEN}7️⃣  配置 Systemd 服務...${NC}"

cat > /etc/systemd/system/vicbot.service <<EOF
[Unit]
Description=VicBot Discord Bot and Web API
After=network.target

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/.venv/bin"
ExecStart=$APP_DIR/.venv/bin/python $APP_DIR/start.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/vicbot/output.log
StandardError=append:/var/log/vicbot/error.log

[Install]
WantedBy=multi-user.target
EOF

# 創建日誌目錄
mkdir -p /var/log/vicbot
chown $APP_USER:$APP_USER /var/log/vicbot

# 重載並啟用服務
systemctl daemon-reload
systemctl enable vicbot

echo -e "${GREEN}✅ Systemd 服務已配置${NC}"
echo ""

# ============ 8. 配置 Nginx ============
echo -e "${GREEN}8️⃣  配置 Nginx 反向代理...${NC}"

cat > /etc/nginx/sites-available/$DOMAIN <<EOF
server {
    listen 80;
    server_name $DOMAIN;

    # 訪問日誌
    access_log /var/log/nginx/${DOMAIN}_access.log;
    error_log /var/log/nginx/${DOMAIN}_error.log;

    # 反向代理到 FastAPI
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # 超時設置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # 靜態文件
    location /static {
        alias $APP_DIR/frontend/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
EOF

# 啟用網站
ln -sf /etc/nginx/sites-available/$DOMAIN /etc/nginx/sites-enabled/

# 測試配置
nginx -t

# 重載 Nginx
systemctl reload nginx

echo -e "${GREEN}✅ Nginx 配置完成${NC}"
echo ""

# ============ 9. 配置 SSL 證書 ============
echo -e "${GREEN}9️⃣  配置 SSL 證書...${NC}"

read -p "是否現在配置 SSL 證書？(需要 DNS 已指向此服務器) [y/N]: " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email admin@honhaihelper.com
    echo -e "${GREEN}✅ SSL 證書已配置${NC}"
else
    echo -e "${YELLOW}⚠️  跳過 SSL 配置，稍後可手動執行:${NC}"
    echo "sudo certbot --nginx -d $DOMAIN"
fi
echo ""

# ============ 10. 啟動服務 ============
echo -e "${GREEN}🔟 啟動 VicBot 服務...${NC}"
systemctl start vicbot

# 等待服務啟動
sleep 5

# 檢查服務狀態
if systemctl is-active --quiet vicbot; then
    echo -e "${GREEN}✅ VicBot 服務已啟動${NC}"
else
    echo -e "${RED}❌ VicBot 服務啟動失敗${NC}"
    echo "查看日誌:"
    echo "  sudo journalctl -u vicbot -n 50"
    exit 1
fi
echo ""

# ============ 11. 防火牆配置 ============
echo -e "${GREEN}1️⃣1️⃣  配置防火牆...${NC}"

# 檢查 UFW 是否安裝
if command -v ufw &> /dev/null; then
    ufw allow 80/tcp
    ufw allow 443/tcp
    ufw allow 22/tcp  # SSH
    echo -e "${GREEN}✅ 防火牆規則已添加${NC}"
else
    echo "UFW 未安裝，請確保 GCP 防火牆規則允許 80、443 端口"
fi
echo ""

# ============ 完成 ============
echo "=================================================="
echo -e "${GREEN}🎉 部署完成！${NC}"
echo "=================================================="
echo ""
echo "📋 部署信息："
echo "  應用目錄: $APP_DIR"
echo "  日誌目錄: /var/log/vicbot/"
echo "  網站地址: https://$DOMAIN"
echo "  API 文檔: https://$DOMAIN/api/docs"
echo ""
echo "📝 常用指令："
echo "  查看服務狀態: sudo systemctl status vicbot"
echo "  重啟服務: sudo systemctl restart vicbot"
echo "  查看日誌: sudo journalctl -u vicbot -f"
echo "  查看應用日誌: sudo tail -f /var/log/vicbot/output.log"
echo ""
echo "🔑 下一步："
echo "  1. 創建管理員帳號:"
echo "     cd $APP_DIR"
echo "     sudo -u $APP_USER .venv/bin/python setup_admin.py"
echo ""
echo "  2. 或使用 API 註冊:"
echo "     curl -X POST \"https://$DOMAIN/api/auth/register\" \\"
echo "       -H \"Content-Type: application/json\" \\"
echo "       -d '{\"discord_id\":你的ID,\"username\":\"admin\",\"guild_id\":伺服器ID,\"password\":\"密碼\",\"role\":\"admin\"}'"
echo ""
echo "  3. 訪問網頁: https://$DOMAIN"
echo ""
echo "=================================================="
