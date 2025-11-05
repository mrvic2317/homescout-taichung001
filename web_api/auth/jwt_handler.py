"""JWT authentication handler for Web API."""
import os
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# JWT 配置
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 小時

# 密碼加密
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer token scheme
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """驗證密碼"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """生成密碼雜湊"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    創建 JWT token

    Args:
        data: 要編碼到 token 的資料
        expires_delta: token 過期時間（可選）

    Returns:
        JWT token 字串
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """
    解碼 JWT token

    Args:
        token: JWT token 字串

    Returns:
        解碼後的資料

    Raises:
        HTTPException: token 無效或過期
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無效的認證憑證",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    從 HTTP Authorization header 獲取當前用戶

    Args:
        credentials: HTTP Bearer 憑證

    Returns:
        用戶資料字典

    Raises:
        HTTPException: 認證失敗
    """
    token = credentials.credentials
    payload = decode_access_token(token)

    discord_id: int = payload.get("discord_id")
    username: str = payload.get("username")
    guild_id: int = payload.get("guild_id")

    if discord_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無效的認證憑證",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "discord_id": discord_id,
        "username": username,
        "guild_id": guild_id,
        "role": payload.get("role", "member")
    }


async def get_current_admin_user(current_user: dict = Depends(get_current_user)) -> dict:
    """
    檢查當前用戶是否為管理員

    Args:
        current_user: 當前用戶資料

    Returns:
        管理員用戶資料

    Raises:
        HTTPException: 用戶非管理員
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理員權限"
        )

    return current_user
