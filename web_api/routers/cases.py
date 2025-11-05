"""Cases endpoints for Web API."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from web_api.models.schemas import Case, CaseCreate, CaseUpdate, CaseUpdateRecord, MessageResponse
from web_api.auth.jwt_handler import get_current_user
from src.services import cases

router = APIRouter(prefix="/cases", tags=["案件"])


@router.post("", response_model=MessageResponse, summary="新增案件")
async def create_case(
    case: CaseCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    新增房產案件

    創建新的案件記錄，可指派給團隊成員。
    """
    case_id = await cases.create_case(
        guild_id=current_user["guild_id"],
        creator_id=current_user["discord_id"],
        title=case.title,
        area=case.area,
        price=case.price,
        status=case.status,
        assignee_id=case.assignee_id,
        notes=case.notes
    )

    return MessageResponse(
        message=f"案件新增成功，編號：{case_id}",
        success=True
    )


@router.get("", response_model=List[Case], summary="查詢案件列表")
async def get_cases(
    status: Optional[str] = Query(None, description="篩選狀態"),
    area: Optional[str] = Query(None, description="篩選區域"),
    current_user: dict = Depends(get_current_user)
):
    """
    查詢案件列表

    可根據狀態和區域篩選，只顯示當前用戶相關的案件。
    """
    case_list = await cases.list_cases(
        guild_id=current_user["guild_id"],
        user_id=current_user["discord_id"],
        status=status,
        area=area
    )

    return [
        Case(
            id=c.id,
            guild_id=c.guild_id,
            creator_id=c.creator_id,
            title=c.title,
            area=c.area,
            price=c.price,
            status=c.status,
            assignee_id=c.assignee_id,
            notes=c.notes,
            created_at=c.created_at,
            updated_at=c.updated_at
        )
        for c in case_list
    ]


@router.get("/{case_id}", response_model=Case, summary="查詢案件詳情")
async def get_case(
    case_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    查詢指定案件的詳細資訊

    只能查看自己創建或被指派的案件。
    """
    case = await cases.get_case(
        case_id=case_id,
        guild_id=current_user["guild_id"]
    )

    if not case:
        raise HTTPException(status_code=404, detail="找不到該案件")

    # 檢查權限：只有創建者或被指派者可以查看
    if current_user["discord_id"] not in (case.creator_id, case.assignee_id):
        raise HTTPException(status_code=403, detail="無權限查看此案件")

    return Case(
        id=case.id,
        guild_id=case.guild_id,
        creator_id=case.creator_id,
        title=case.title,
        area=case.area,
        price=case.price,
        status=case.status,
        assignee_id=case.assignee_id,
        notes=case.notes,
        created_at=case.created_at,
        updated_at=case.updated_at
    )


@router.put("/{case_id}", response_model=MessageResponse, summary="更新案件")
async def update_case(
    case_id: int,
    case_update: CaseUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    更新案件狀態或備註

    只能更新自己創建或被指派的案件。
    """
    success = await cases.update_case(
        case_id=case_id,
        guild_id=current_user["guild_id"],
        user_id=current_user["discord_id"],
        status=case_update.status,
        note=case_update.note
    )

    if not success:
        raise HTTPException(status_code=404, detail="找不到該案件或無權限更新")

    return MessageResponse(
        message=f"案件已更新（編號：{case_id}）",
        success=True
    )


@router.get("/{case_id}/updates", response_model=List[CaseUpdateRecord], summary="查詢案件更新記錄")
async def get_case_updates(
    case_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    查詢案件的所有更新記錄

    需要有查看案件的權限。
    """
    # 先檢查是否有權限查看案件
    case = await cases.get_case(
        case_id=case_id,
        guild_id=current_user["guild_id"]
    )

    if not case:
        raise HTTPException(status_code=404, detail="找不到該案件")

    if current_user["discord_id"] not in (case.creator_id, case.assignee_id):
        raise HTTPException(status_code=403, detail="無權限查看此案件")

    # 獲取更新記錄
    updates = await cases.list_case_updates(case_id=case_id)

    return [
        CaseUpdateRecord(
            id=u.id,
            case_id=u.case_id,
            user_id=u.user_id,
            status=u.status,
            note=u.note,
            created_at=u.created_at
        )
        for u in updates
    ]
