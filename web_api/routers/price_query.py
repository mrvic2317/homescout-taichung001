"""Price query endpoints for Web API."""
from fastapi import APIRouter, Depends
from web_api.models.schemas import PriceQueryRequest, PriceStats, ProjectGroup
from web_api.auth.jwt_handler import get_current_user
from src.services import price_query

router = APIRouter(prefix="/price", tags=["房價查詢"])


@router.post("/query", response_model=PriceStats, summary="查詢房價統計")
async def query_price(
    request: PriceQueryRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    查詢台中市房價統計資料

    根據地區名稱查詢實價登錄資料，包含價格統計和建案分組。
    """
    stats = await price_query.query_price(request.area, use_cache=True)

    # 轉換 project_groups
    project_groups = [
        ProjectGroup(
            road_name=group.road_name,
            address_range=group.address_range,
            transaction_count=group.transaction_count,
            avg_price=group.avg_price,
            avg_unit_price=group.avg_unit_price,
            addresses=group.addresses
        )
        for group in stats.project_groups
    ]

    return PriceStats(
        area=stats.area,
        query_period=stats.query_period,
        total_transactions=stats.total_transactions,
        avg_price=stats.avg_price,
        avg_unit_price=stats.avg_unit_price,
        max_price=stats.max_price,
        min_price=stats.min_price,
        max_unit_price=stats.max_unit_price,
        min_unit_price=stats.min_unit_price,
        project_groups=project_groups
    )
