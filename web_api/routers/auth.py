"""Authentication endpoints for Web API."""
from fastapi import APIRouter, HTTPException, status, Depends
from web_api.models.schemas import Token, UserLogin, User, MessageResponse
from web_api.auth.jwt_handler import create_access_token, get_current_user
from web_api.auth.users import authenticate_user, create_user, get_user_by_discord_id

router = APIRouter(prefix="/auth", tags=["認證"])


@router.post("/login", response_model=Token, summary="用戶登入")
async def login(user_login: UserLogin):
    """
    用戶登入

    使用 Discord ID 和密碼登入，成功後返回 JWT token。
    """
    user = await authenticate_user(user_login.discord_id, user_login.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Discord ID 或密碼錯誤",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 創建 access token
    access_token = create_access_token(
        data={
            "discord_id": user["discord_id"],
            "username": user["username"],
            "guild_id": user["guild_id"],
            "role": user["role"]
        }
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/register", response_model=MessageResponse, summary="註冊新用戶")
async def register(
    discord_id: int,
    username: str,
    guild_id: int,
    password: str,
    role: str = "member"
):
    """
    註冊新用戶

    創建新的 Web API 用戶帳號。需要提供 Discord ID、用戶名、伺服器 ID 和密碼。
    """
    # 檢查用戶是否已存在
    existing_user = await get_user_by_discord_id(discord_id)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="該 Discord ID 已註冊"
        )

    # 創建新用戶
    user_id = await create_user(discord_id, username, guild_id, password, role)

    return MessageResponse(
        message=f"用戶註冊成功，ID: {user_id}",
        success=True
    )


@router.get("/me", response_model=User, summary="獲取當前用戶資訊")
async def get_me(current_user: dict = Depends(get_current_user)):
    """
    獲取當前登入用戶的資訊

    需要提供有效的 JWT token。
    """
    return User(
        discord_id=current_user["discord_id"],
        username=current_user["username"],
        guild_id=current_user["guild_id"],
        role=current_user.get("role", "member")
    )


@router.post("/refresh", response_model=Token, summary="刷新 Token")
async def refresh_token(current_user: dict = Depends(get_current_user)):
    """
    刷新 JWT token

    使用現有的有效 token 獲取新的 token。
    """
    access_token = create_access_token(
        data={
            "discord_id": current_user["discord_id"],
            "username": current_user["username"],
            "guild_id": current_user["guild_id"],
            "role": current_user["role"]
        }
    )

    return {"access_token": access_token, "token_type": "bearer"}
