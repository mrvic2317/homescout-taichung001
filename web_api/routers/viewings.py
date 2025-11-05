"""Viewings endpoints for Web API."""
from typing import List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from web_api.models.schemas import Viewing, ViewingCreate, MessageResponse
from web_api.auth.jwt_handler import get_current_user
from src.services import viewings

router = APIRouter(prefix="/viewings", tags=["看屋"])


@router.post("", response_model=MessageResponse, summary="新增看屋排程")
async def create_viewing(
    viewing: ViewingCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    新增看屋排程

    創建新的看屋行程，系統會在預定時間前 90 分鐘發送提醒。
    """
    viewing_id = await viewings.add_viewing(
        guild_id=current_user["guild_id"],
        creator_id=current_user["discord_id"],
        scheduled_at=viewing.scheduled_at,
        client=viewing.client,
        property=viewing.property,
        agent=viewing.agent,
        contact=viewing.contact,
        note=viewing.note,
        link=viewing.link
    )

    return MessageResponse(
        message=f"看屋排程已建立，編號：{viewing_id}",
        success=True
    )


@router.get("", response_model=List[Viewing], summary="查詢看屋列表")
async def get_viewings(
    days: int = Query(7, description="查詢未來幾天的排程"),
    current_user: dict = Depends(get_current_user)
):
    """
    查詢看屋排程列表

    預設顯示未來 7 天的看屋行程。
    """
    until = datetime.utcnow() + timedelta(days=days)

    viewing_list = await viewings.list_viewings(
        guild_id=current_user["guild_id"],
        creator_id=current_user["discord_id"],
        until=until
    )

    return [
        Viewing(
            id=v.id,
            guild_id=v.guild_id,
            creator_id=v.creator_id,
            scheduled_at=datetime.fromisoformat(v.scheduled_at),
            client=v.client,
            property=v.property,
            agent=v.agent,
            contact=v.contact,
            note=v.note,
            link=v.link,
            reminded=v.reminded,
            created_at=v.created_at
        )
        for v in viewing_list
    ]
