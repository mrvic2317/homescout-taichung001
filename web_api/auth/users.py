"""User management for Web API."""
from typing import Optional
import aiosqlite
from web_api.auth.jwt_handler import get_password_hash, verify_password


async def init_users_table(db_path: str = "vicbot.db") -> None:
    """初始化用戶表"""
    async with aiosqlite.connect(db_path) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS web_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discord_id INTEGER UNIQUE NOT NULL,
                username TEXT NOT NULL,
                guild_id INTEGER NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'member',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()


async def create_user(
    discord_id: int,
    username: str,
    guild_id: int,
    password: str,
    role: str = "member",
    db_path: str = "vicbot.db"
) -> int:
    """
    創建新用戶

    Args:
        discord_id: Discord 用戶 ID
        username: 用戶名稱
        guild_id: Discord 伺服器 ID
        password: 密碼
        role: 角色 (member/admin)
        db_path: 資料庫路徑

    Returns:
        新用戶 ID
    """
    password_hash = get_password_hash(password)

    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            """
            INSERT INTO web_users (discord_id, username, guild_id, password_hash, role)
            VALUES (?, ?, ?, ?, ?)
            """,
            (discord_id, username, guild_id, password_hash, role)
        )
        await db.commit()
        return cursor.lastrowid


async def authenticate_user(
    discord_id: int,
    password: str,
    db_path: str = "vicbot.db"
) -> Optional[dict]:
    """
    驗證用戶登入

    Args:
        discord_id: Discord 用戶 ID
        password: 密碼
        db_path: 資料庫路徑

    Returns:
        用戶資料（驗證成功）或 None（驗證失敗）
    """
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM web_users WHERE discord_id = ?",
            (discord_id,)
        ) as cursor:
            user = await cursor.fetchone()

    if not user:
        return None

    if not verify_password(password, user["password_hash"]):
        return None

    return {
        "id": user["id"],
        "discord_id": user["discord_id"],
        "username": user["username"],
        "guild_id": user["guild_id"],
        "role": user["role"]
    }


async def get_user_by_discord_id(
    discord_id: int,
    db_path: str = "vicbot.db"
) -> Optional[dict]:
    """
    根據 Discord ID 獲取用戶

    Args:
        discord_id: Discord 用戶 ID
        db_path: 資料庫路徑

    Returns:
        用戶資料或 None
    """
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, discord_id, username, guild_id, role FROM web_users WHERE discord_id = ?",
            (discord_id,)
        ) as cursor:
            user = await cursor.fetchone()

    if not user:
        return None

    return {
        "id": user["id"],
        "discord_id": user["discord_id"],
        "username": user["username"],
        "guild_id": user["guild_id"],
        "role": user["role"]
    }


async def update_user_password(
    discord_id: int,
    new_password: str,
    db_path: str = "vicbot.db"
) -> bool:
    """
    更新用戶密碼

    Args:
        discord_id: Discord 用戶 ID
        new_password: 新密碼
        db_path: 資料庫路徑

    Returns:
        是否更新成功
    """
    password_hash = get_password_hash(new_password)

    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "UPDATE web_users SET password_hash = ? WHERE discord_id = ?",
            (password_hash, discord_id)
        )
        await db.commit()
        return cursor.rowcount > 0
