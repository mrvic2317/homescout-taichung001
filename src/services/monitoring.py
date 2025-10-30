"""Monitoring service for VicBot."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import aiosqlite

from .. import database


@dataclass
class MonitoringRule:
    id: int
    user_id: int
    guild_id: int
    area: str
    price_min: Optional[int]
    price_max: Optional[int]
    size_min: Optional[float]
    size_max: Optional[float]


async def add_rule(
    *,
    user_id: int,
    guild_id: int,
    area: str,
    price_min: Optional[int],
    price_max: Optional[int],
    size_min: Optional[float],
    size_max: Optional[float],
) -> int:
    async with database.connect() as db:
        cursor = await db.execute(
            """
            INSERT INTO monitoring (user_id, guild_id, area, price_min, price_max, size_min, size_max)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, guild_id, area, price_min, price_max, size_min, size_max),
        )
        await db.commit()
        return cursor.lastrowid


async def list_rules(*, user_id: int, guild_id: int) -> List[MonitoringRule]:
    async with database.connect() as db:
        cursor = await db.execute(
            "SELECT * FROM monitoring WHERE user_id = ? AND guild_id = ? ORDER BY id",
            (user_id, guild_id),
        )
        rows = await cursor.fetchall()
        return [MonitoringRule(**dict(row)) for row in rows]


async def delete_rule(*, rule_id: int, user_id: int, guild_id: int) -> bool:
    async with database.connect() as db:
        cursor = await db.execute(
            "DELETE FROM monitoring WHERE id = ? AND user_id = ? AND guild_id = ?",
            (rule_id, user_id, guild_id),
        )
        await db.commit()
        return cursor.rowcount > 0


async def iter_rules(db: aiosqlite.Connection) -> List[MonitoringRule]:
    cursor = await db.execute("SELECT * FROM monitoring")
    rows = await cursor.fetchall()
    return [MonitoringRule(**dict(row)) for row in rows]
