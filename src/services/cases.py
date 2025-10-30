"""Case management service."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .. import database


@dataclass
class Case:
    id: int
    guild_id: int
    creator_id: int
    title: str
    area: Optional[str]
    price: Optional[int]
    status: str
    assignee_id: Optional[int]
    notes: Optional[str]
    created_at: str
    updated_at: str


@dataclass
class CaseUpdate:
    id: int
    case_id: int
    user_id: int
    status: Optional[str]
    note: Optional[str]
    created_at: str


async def create_case(
    *,
    guild_id: int,
    creator_id: int,
    title: str,
    area: Optional[str],
    price: Optional[int],
    status: str,
    assignee_id: Optional[int],
    notes: Optional[str] = None,
) -> int:
    async with database.connect() as db:
        cursor = await db.execute(
            """
            INSERT INTO cases (guild_id, creator_id, title, area, price, status, assignee_id, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (guild_id, creator_id, title, area, price, status, assignee_id, notes),
        )
        case_id = cursor.lastrowid
        await db.execute(
            """
            INSERT INTO case_updates (case_id, user_id, status, note)
            VALUES (?, ?, ?, ?)
            """,
            (case_id, creator_id, status, notes),
        )
        await db.commit()
        return case_id


async def list_cases(
    *,
    guild_id: int,
    user_id: int,
    status: Optional[str] = None,
    area: Optional[str] = None,
) -> List[Case]:
    query = """
        SELECT DISTINCT c.*
        FROM cases c
        LEFT JOIN case_updates cu ON cu.case_id = c.id
        WHERE c.guild_id = ?
          AND (c.creator_id = ? OR c.assignee_id = ? OR cu.user_id = ?)
    """
    params: List[object] = [guild_id, user_id, user_id, user_id]

    if status:
        query += " AND c.status = ?"
        params.append(status)
    if area:
        query += " AND c.area = ?"
        params.append(area)

    query += " ORDER BY c.updated_at DESC"

    async with database.connect() as db:
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        return [Case(**dict(row)) for row in rows]


async def update_case(
    *,
    case_id: int,
    guild_id: int,
    user_id: int,
    status: Optional[str],
    note: Optional[str],
) -> bool:
    async with database.connect() as db:
        cursor = await db.execute(
            "SELECT creator_id, assignee_id FROM cases WHERE id = ? AND guild_id = ?",
            (case_id, guild_id),
        )
        row = await cursor.fetchone()
        if not row:
            return False
        if user_id not in (row["creator_id"], row["assignee_id"]):
            return False

        updates = []
        params: List[object] = []
        if status:
            updates.append("status = ?")
            params.append(status)
        if note:
            updates.append("notes = ?")
            params.append(note)
        if updates:
            params.extend([case_id, guild_id])
            await db.execute(
                f"UPDATE cases SET {', '.join(updates)} WHERE id = ? AND guild_id = ?",
                params,
            )
        await db.execute(
            """
            INSERT INTO case_updates (case_id, user_id, status, note)
            VALUES (?, ?, ?, ?)
            """,
            (case_id, user_id, status, note),
        )
        await db.commit()
        return True


async def get_case(*, case_id: int, guild_id: int) -> Optional[Case]:
    async with database.connect() as db:
        cursor = await db.execute(
            "SELECT * FROM cases WHERE id = ? AND guild_id = ?",
            (case_id, guild_id),
        )
        row = await cursor.fetchone()
        return Case(**dict(row)) if row else None


async def list_case_updates(*, case_id: int) -> List[CaseUpdate]:
    async with database.connect() as db:
        cursor = await db.execute(
            "SELECT * FROM case_updates WHERE case_id = ? ORDER BY created_at DESC",
            (case_id,),
        )
        rows = await cursor.fetchall()
        return [CaseUpdate(**dict(row)) for row in rows]
