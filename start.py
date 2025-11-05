"""
VicBot 整合啟動腳本

同時運行 Discord Bot 和 Web API
"""
import asyncio
import multiprocessing
import os
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_discord_bot():
    """運行 Discord Bot"""
    logger.info("🤖 啟動 Discord Bot...")
    try:
        import bot
        asyncio.run(bot.main())
    except Exception as e:
        logger.error(f"❌ Discord Bot 啟動失敗: {e}")
        sys.exit(1)


def run_web_api():
    """運行 Web API"""
    logger.info("🌐 啟動 Web API...")
    try:
        import uvicorn
        from web_api.main import app

        uvicorn.run(
            app,
            host="0.0.0.0",
            port=int(os.getenv("PORT", 8000)),
            log_level="info"
        )
    except Exception as e:
        logger.error(f"❌ Web API 啟動失敗: {e}")
        sys.exit(1)


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("🚀 VicBot 整合系統啟動中...")
    logger.info("=" * 60)

    # 檢查環境變數
    if not os.getenv("DISCORD_TOKEN"):
        logger.error("❌ 缺少 DISCORD_TOKEN 環境變數")
        sys.exit(1)

    # 創建進程
    discord_process = multiprocessing.Process(target=run_discord_bot, name="DiscordBot")
    web_process = multiprocessing.Process(target=run_web_api, name="WebAPI")

    try:
        # 啟動進程
        discord_process.start()
        web_process.start()

        logger.info("✅ Discord Bot 和 Web API 已啟動")
        logger.info("📊 儀表板：http://localhost:8000")
        logger.info("📖 API 文檔：http://localhost:8000/api/docs")

        # 等待進程
        discord_process.join()
        web_process.join()

    except KeyboardInterrupt:
        logger.info("⏹️  收到停止信號，正在關閉...")

        # 優雅關閉
        discord_process.terminate()
        web_process.terminate()

        discord_process.join(timeout=5)
        web_process.join(timeout=5)

        logger.info("👋 VicBot 已關閉")

    except Exception as e:
        logger.error(f"❌ 啟動失敗: {e}")

        # 清理進程
        if discord_process.is_alive():
            discord_process.terminate()
        if web_process.is_alive():
            web_process.terminate()

        sys.exit(1)
