"""Clients endpoints for Web API."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from web_api.models.schemas import Client, ClientCreate, ClientUpdate, ClientFollowup, ClientFollowupCreate, MessageResponse
from web_api.auth.jwt_handler import get_current_user
from src.services import clients

router = APIRouter(prefix="/clients", tags=["客戶"])


@router.post("", response_model=MessageResponse, summary="新增客戶")
async def create_client(
    client: ClientCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    新增客戶資料

    創建新的客戶記錄，包含預算、偏好區域等資訊。
    """
    client_id = await clients.create_client(
        guild_id=current_user["guild_id"],
        owner_id=current_user["discord_id"],
        name=client.name,
        budget_min=client.budget_min,
        budget_max=client.budget_max,
        preferred_areas=client.preferred_areas,
        description=client.description
    )

    return MessageResponse(
        message=f"客戶新增成功，編號：{client_id}",
        success=True
    )


@router.get("", response_model=List[Client], summary="查詢客戶列表")
async def get_clients(current_user: dict = Depends(get_current_user)):
    """
    查詢當前用戶的所有客戶資料
    """
    client_list = await clients.list_clients(
        guild_id=current_user["guild_id"],
        owner_id=current_user["discord_id"]
    )

    return [
        Client(
            id=c.id,
            guild_id=c.guild_id,
            owner_id=c.owner_id,
            name=c.name,
            budget_min=c.budget_min,
            budget_max=c.budget_max,
            preferred_areas=c.preferred_areas,
            description=c.description,
            created_at=c.created_at,
            updated_at=c.updated_at
        )
        for c in client_list
    ]


@router.get("/{client_id}", response_model=Client, summary="查詢客戶詳情")
async def get_client(
    client_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    查詢指定客戶的詳細資訊

    只能查看自己的客戶。
    """
    # 透過 list_clients 取得，自動檢查權限
    client_list = await clients.list_clients(
        guild_id=current_user["guild_id"],
        owner_id=current_user["discord_id"]
    )

    client = next((c for c in client_list if c.id == client_id), None)

    if not client:
        raise HTTPException(status_code=404, detail="找不到該客戶或無權限查看")

    return Client(
        id=client.id,
        guild_id=client.guild_id,
        owner_id=client.owner_id,
        name=client.name,
        budget_min=client.budget_min,
        budget_max=client.budget_max,
        preferred_areas=client.preferred_areas,
        description=client.description,
        created_at=client.created_at,
        updated_at=client.updated_at
    )


@router.put("/{client_id}", response_model=MessageResponse, summary="更新客戶資料")
async def update_client(
    client_id: int,
    client_update: ClientUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    更新客戶資料

    只能更新自己的客戶。
    """
    updates = {}
    if client_update.name is not None:
        updates["name"] = client_update.name
    if client_update.budget_min is not None:
        updates["budget_min"] = client_update.budget_min
    if client_update.budget_max is not None:
        updates["budget_max"] = client_update.budget_max
    if client_update.preferred_areas is not None:
        updates["preferred_areas"] = client_update.preferred_areas
    if client_update.description is not None:
        updates["description"] = client_update.description

    success = await clients.update_client(
        client_id=client_id,
        guild_id=current_user["guild_id"],
        owner_id=current_user["discord_id"],
        updates=updates
    )

    if not success:
        raise HTTPException(status_code=404, detail="找不到該客戶或無權限更新")

    return MessageResponse(
        message=f"客戶資料已更新（編號：{client_id}）",
        success=True
    )


@router.post("/{client_id}/followups", response_model=MessageResponse, summary="新增跟進記錄")
async def add_followup(
    client_id: int,
    followup: ClientFollowupCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    為客戶新增跟進記錄

    記錄與客戶的互動、需求變更等資訊。
    """
    success = await clients.add_followup(
        client_id=client_id,
        guild_id=current_user["guild_id"],
        user_id=current_user["discord_id"],
        note=followup.note
    )

    if not success:
        raise HTTPException(status_code=404, detail="找不到該客戶或無權限新增")

    return MessageResponse(
        message="跟進記錄已新增",
        success=True
    )


@router.get("/{client_id}/followups", response_model=List[ClientFollowup], summary="查詢跟進記錄")
async def get_followups(
    client_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    查詢客戶的所有跟進記錄

    只能查看自己客戶的跟進記錄。
    """
    followups = await clients.list_followups(
        client_id=client_id,
        guild_id=current_user["guild_id"],
        owner_id=current_user["discord_id"]
    )

    if followups is None:
        raise HTTPException(status_code=404, detail="找不到該客戶或無權限查看")

    return [
        ClientFollowup(
            id=f.id,
            client_id=f.client_id,
            user_id=f.user_id,
            note=f.note,
            created_at=f.created_at
        )
        for f in followups
    ]
