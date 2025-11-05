# VicBot Dockerfile
FROM python:3.11-slim

# 設定工作目錄
WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 複製依賴文件
COPY requirements.txt .

# 安裝 Python 依賴
RUN pip install --no-cache-dir -r requirements.txt

# 複製專案文件
COPY . .

# 創建資料目錄
RUN mkdir -p data frontend/static frontend/templates

# 暴露端口
EXPOSE 8000

# 啟動應用
CMD ["python", "start.py"]
