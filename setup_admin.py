"""
VicBot Web 管理員帳號設置腳本

快速創建管理員帳號
"""
import asyncio
import os
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

async def main():
    print("=" * 60)
    print("🔧 VicBot Web 管理員帳號設置")
    print("=" * 60)
    print()

    # 導入模組
    from web_api.auth.users import init_users_table, create_user, get_user_by_discord_id
    from src.database import init_db

    # 初始化資料庫
    print("📦 初始化資料庫...")
    await init_db()
    await init_users_table()
    print("✅ 資料庫初始化完成")
    print()

    # 獲取用戶輸入
    print("請輸入管理員資訊：")
    print()

    try:
        discord_id = int(input("Discord ID（右鍵點擊頭像複製）: "))
        username = input("用戶名稱: ")
        guild_id = int(input("Discord 伺服器 ID（右鍵點擊伺服器圖示複製）: "))
        password = input("密碼: ")
        confirm_password = input("確認密碼: ")

        # 驗證密碼
        if password != confirm_password:
            print("❌ 密碼不一致！")
            return

        # 檢查用戶是否已存在
        existing_user = await get_user_by_discord_id(discord_id)
        if existing_user:
            print(f"⚠️  Discord ID {discord_id} 已註冊")
            choice = input("是否要重置密碼？(y/n): ")
            if choice.lower() == 'y':
                from web_api.auth.users import update_user_password
                success = await update_user_password(discord_id, password)
                if success:
                    print("✅ 密碼已重置")
                else:
                    print("❌ 密碼重置失敗")
            return

        # 創建管理員帳號
        print()
        print("創建管理員帳號...")
        user_id = await create_user(
            discord_id=discord_id,
            username=username,
            guild_id=guild_id,
            password=password,
            role="admin"
        )

        print()
        print("=" * 60)
        print("✅ 管理員帳號創建成功！")
        print("=" * 60)
        print()
        print(f"📝 帳號資訊：")
        print(f"   用戶 ID: {user_id}")
        print(f"   Discord ID: {discord_id}")
        print(f"   用戶名稱: {username}")
        print(f"   伺服器 ID: {guild_id}")
        print(f"   角色: 管理員")
        print()
        print("🌐 現在可以使用以下資訊登入網頁管理面板：")
        print(f"   Discord ID: {discord_id}")
        print(f"   密碼: [您設定的密碼]")
        print()
        print("📖 下一步：")
        print("   1. 啟動應用：python start.py")
        print("   2. 訪問 http://localhost:8000")
        print("   3. 使用上述資訊登入")
        print()

    except ValueError:
        print("❌ 輸入格式錯誤！Discord ID 和伺服器 ID 必須是數字。")
    except KeyboardInterrupt:
        print("\n\n⏹️  設置已取消")
    except Exception as e:
        print(f"\n❌ 設置失敗：{e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⏹️  設置已取消")
