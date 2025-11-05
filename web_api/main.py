"""VicBot Web API - FastAPI application."""
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
import logging

from web_api.routers import auth, monitoring, cases, clients, viewings, price_query
from web_api.auth.users import init_users_table
from src import database

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用程式生命週期管理"""
    # 啟動時執行
    logger.info("🚀 VicBot Web API 啟動中...")

    # 初始化資料庫
    await database.init_db()
    await init_users_table()

    logger.info("✅ 資料庫初始化完成")

    yield

    # 關閉時執行
    logger.info("👋 VicBot Web API 關閉")


# 創建 FastAPI 應用
app = FastAPI(
    title="VicBot Web API",
    description="VicBot 房仲管理系統 Web API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# CORS 設定（允許前端跨域請求）
origins = [
    "http://localhost:3000",
    "http://localhost:8080",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8080",
    # 生產環境需要加入實際的前端網址
    os.getenv("FRONTEND_URL", ""),
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 全域異常處理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"全域異常：{exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "伺服器內部錯誤",
            "success": False
        }
    )


# 註冊路由
app.include_router(auth.router, prefix="/api")
app.include_router(monitoring.router, prefix="/api")
app.include_router(cases.router, prefix="/api")
app.include_router(clients.router, prefix="/api")
app.include_router(viewings.router, prefix="/api")
app.include_router(price_query.router, prefix="/api")


# 靜態檔案和模板（用於前端）
try:
    app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
    templates = Jinja2Templates(directory="frontend/templates")
except RuntimeError:
    logger.warning("前端檔案目錄不存在，跳過靜態檔案掛載")
    templates = None


@app.get("/", tags=["首頁"])
async def root():
    """API 根路徑"""
    return {
        "message": "歡迎使用 VicBot Web API",
        "version": "1.0.0",
        "docs": "/api/docs",
        "api_prefix": "/api"
    }


@app.get("/health", tags=["健康檢查"])
async def health_check():
    """健康檢查端點（用於部署監控）"""
    return {
        "status": "healthy",
        "service": "VicBot Web API",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "web_api.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True
    )
