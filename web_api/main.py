"""VicBot Web API - FastAPI application."""
import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging

# 載入環境變數
load_dotenv()

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
    "https://vicbot.honhaihelper.com",
    "http://vicbot.honhaihelper.com",
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


# 靜態檔案（React build）
try:
    # Mount React app's built assets
    app.mount("/assets", StaticFiles(directory="frontend-react/dist/assets"), name="assets")
    logger.info("✅ React 靜態資源已掛載")

    # 處理根路徑和所有前端路由
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        return FileResponse("frontend-react/dist/index.html")

    logger.info("✅ 前端路由處理已設置")
except RuntimeError as e:
    logger.warning(f"⚠️ 靜態資源掛載失敗: {str(e)}")


@app.get("/health", tags=["健康檢查"])
async def health_check():
    """健康檢查端點（用於部署監控）"""
    return {
        "status": "healthy",
        "service": "VicBot Web API",
        "version": "1.0.0"
    }


# Catch-all route to serve React app (must be last)
@app.get("/{full_path:path}", tags=["前端"])
async def serve_react_app(full_path: str):
    """服務 React 單頁應用程式"""
    # Serve index.html for all non-API routes
    if not full_path.startswith("api/"):
        index_path = os.path.join("frontend-react", "dist", "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)

    # If React build doesn't exist, return a helpful message
    return {
        "message": "VicBot Web API",
        "version": "1.0.0",
        "docs": "/api/docs",
        "note": "React 前端尚未建置，請執行: cd frontend-react && npm run build"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "web_api.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True
    )
