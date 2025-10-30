"""Viewing schedule service."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from .. import database


@dataclass
class Viewing:
    id: int
    guild_id: int
    creator_id: int
    scheduled_at: str
    client: str
    property: str
    agent: Optional[str]
    contact: Optional[str]
    note: Optional[str]
    link: Optional[str]
    reminded: int
    created_at: str


async def add_viewing(
    *,
    guild_id: int,
    creator_id: int,
    scheduled_at: datetime,
    client: str,
    property: str,
    agent: Optional[str],
    contact: Optional[str],
    note: Optional[str],
    link: Optional[str],
) -> int:
    async with database.connect() as db:
        cursor = await db.execute(
            """
            INSERT INTO viewings (guild_id, creator_id, scheduled_at, client, property, agent, contact, note, link)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                guild_id,
                creator_id,
                scheduled_at.isoformat(),
                client,
                property,
                agent,
                contact,
                note,
                link,
            ),
        )
        await db.commit()
        return cursor.lastrowid


async def list_viewings(
    *,
    guild_id: int,
    creator_id: int,
    until: Optional[datetime] = None,
) -> List[Viewing]:
    query = "SELECT * FROM viewings WHERE guild_id = ? AND creator_id = ?"
    params: List[object] = [guild_id, creator_id]
    if until:
        query += " AND scheduled_at <= ?"
        params.append(until.isoformat())
    query += " ORDER BY scheduled_at"

    async with database.connect() as db:
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        return [Viewing(**dict(row)) for row in rows]


async def pending_reminders(*, before: datetime) -> List[Viewing]:
    async with database.connect() as db:
        cursor = await db.execute(
            """
            SELECT * FROM viewings
            WHERE reminded = 0 AND scheduled_at <= ?
            """,
            (before.isoformat(),),
        )
        rows = await cursor.fetchall()
        return [Viewing(**dict(row)) for row in rows]


async def mark_reminded(viewing_id: int) -> None:
    async with database.connect() as db:
        await db.execute(
            "UPDATE viewings SET reminded = 1 WHERE id = ?",
            (viewing_id,),
        )
        await db.commit()
