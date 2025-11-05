"""Monitoring endpoints for Web API."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from web_api.models.schemas import MonitoringRule, MonitoringRuleCreate, MessageResponse
from web_api.auth.jwt_handler import get_current_user
from src.services import monitoring

router = APIRouter(prefix="/monitoring", tags=["監控"])


@router.post("", response_model=MessageResponse, summary="新增監控條件")
async def create_monitoring_rule(
    rule: MonitoringRuleCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    新增房源監控條件

    創建新的監控規則，系統會自動推送符合條件的房源。
    """
    rule_id = await monitoring.add_rule(
        user_id=current_user["discord_id"],
        guild_id=current_user["guild_id"],
        area=rule.area,
        price_min=rule.price_min,
        price_max=rule.price_max,
        size_min=rule.size_min,
        size_max=rule.size_max
    )

    return MessageResponse(
        message=f"監控條件新增成功，編號：{rule_id}",
        success=True
    )


@router.get("", response_model=List[MonitoringRule], summary="查詢監控列表")
async def get_monitoring_rules(current_user: dict = Depends(get_current_user)):
    """
    查詢當前用戶的所有監控條件
    """
    rules = await monitoring.list_rules(
        user_id=current_user["discord_id"],
        guild_id=current_user["guild_id"]
    )

    return [
        MonitoringRule(
            id=rule.id,
            user_id=rule.user_id,
            guild_id=rule.guild_id,
            area=rule.area,
            price_min=rule.price_min,
            price_max=rule.price_max,
            size_min=rule.size_min,
            size_max=rule.size_max,
            created_at=rule.created_at
        )
        for rule in rules
    ]


@router.delete("/{rule_id}", response_model=MessageResponse, summary="刪除監控條件")
async def delete_monitoring_rule(
    rule_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    刪除指定的監控條件

    只能刪除自己創建的監控條件。
    """
    success = await monitoring.delete_rule(
        rule_id=rule_id,
        user_id=current_user["discord_id"],
        guild_id=current_user["guild_id"]
    )

    if not success:
        raise HTTPException(status_code=404, detail="找不到該監控條件或無權限刪除")

    return MessageResponse(
        message=f"監控條件已刪除（編號：{rule_id}）",
        success=True
    )
