"""Market data service integrating with MOI real price registration."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List, Optional


@dataclass
class Listing:
    area: str
    price: int
    size: float
    address: str
    building_type: Optional[str] = None
    url: Optional[str] = None
    updated_at: Optional[datetime] = None


async def fetch_latest_listings(
    area: str,
    price_min: Optional[int],
    price_max: Optional[int],
    size_min: Optional[float],
    size_max: Optional[float],
    limit: int = 5,
) -> List[Listing]:
    """Fetch latest listings from the authorised open data source.

    This is a placeholder implementation that should be replaced with an
    integration with the Ministry of Interior real price registration API.
    The function currently returns an empty list but keeps the interface ready
    for the production integration.
    """

    await asyncio.sleep(0)
    return []


@dataclass
class MarketSummary:
    area: str
    average_price: Optional[float]
    median_price: Optional[float]
    transactions: int
    sample_period_days: int


async def fetch_market_summary(area: str, days: int) -> MarketSummary:
    await asyncio.sleep(0)
    return MarketSummary(
        area=area,
        average_price=None,
        median_price=None,
        transactions=0,
        sample_period_days=days,
    )


async def generate_report(areas: Iterable[str], days: int) -> str:
    summaries = await asyncio.gather(*(fetch_market_summary(area, days) for area in areas))

    lines = [f"市場行情報表（近 {days} 天）"]
    for summary in summaries:
        avg = f"{summary.average_price:.0f}" if summary.average_price else "N/A"
        med = f"{summary.median_price:.0f}" if summary.median_price else "N/A"
        lines.append(
            f"- {summary.area}: 平均單價 {avg} 萬/坪，成交中位數 {med} 萬/坪，交易量 {summary.transactions} 件"
        )
    return "\n".join(lines)
