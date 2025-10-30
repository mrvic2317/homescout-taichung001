"""Client management service."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .. import database


@dataclass
class Client:
    id: int
    guild_id: int
    owner_id: int
    name: str
    budget_min: Optional[int]
    budget_max: Optional[int]
    preferred_areas: Optional[str]
    description: Optional[str]
    created_at: str
    updated_at: str


@dataclass
class ClientFollowup:
    id: int
    client_id: int
    user_id: int
    note: str
    created_at: str


async def create_client(
    *,
    guild_id: int,
    owner_id: int,
    name: str,
    budget_min: Optional[int],
    budget_max: Optional[int],
    preferred_areas: Optional[str],
    description: Optional[str],
) -> int:
    async with database.connect() as db:
        cursor = await db.execute(
            """
            INSERT INTO clients (guild_id, owner_id, name, budget_min, budget_max, preferred_areas, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (guild_id, owner_id, name, budget_min, budget_max, preferred_areas, description),
        )
        await db.commit()
        return cursor.lastrowid


async def list_clients(*, guild_id: int, owner_id: int) -> List[Client]:
    async with database.connect() as db:
        cursor = await db.execute(
            "SELECT * FROM clients WHERE guild_id = ? AND owner_id = ? ORDER BY updated_at DESC",
            (guild_id, owner_id),
        )
        rows = await cursor.fetchall()
        return [Client(**dict(row)) for row in rows]


async def update_client(
    *,
    client_id: int,
    guild_id: int,
    owner_id: int,
    updates: dict,
) -> bool:
    if not updates:
        return False

    async with database.connect() as db:
        cursor = await db.execute(
            "SELECT owner_id FROM clients WHERE id = ? AND guild_id = ?",
            (client_id, guild_id),
        )
        row = await cursor.fetchone()
        if not row or row["owner_id"] != owner_id:
            return False

        columns = ", ".join(f"{key} = ?" for key in updates)
        values = list(updates.values()) + [client_id, guild_id]
        await db.execute(
            f"UPDATE clients SET {columns} WHERE id = ? AND guild_id = ?",
            values,
        )
        await db.commit()
        return True


async def add_followup(
    *,
    client_id: int,
    guild_id: int,
    user_id: int,
    note: str,
) -> bool:
    async with database.connect() as db:
        cursor = await db.execute(
            "SELECT owner_id FROM clients WHERE id = ? AND guild_id = ?",
            (client_id, guild_id),
        )
        row = await cursor.fetchone()
        if not row or row["owner_id"] != user_id:
            return False

        await db.execute(
            "INSERT INTO client_followups (client_id, user_id, note) VALUES (?, ?, ?)",
            (client_id, user_id, note),
        )
        await db.commit()
        return True


async def list_followups(*, client_id: int, guild_id: int, owner_id: int) -> Optional[List[ClientFollowup]]:
    async with database.connect() as db:
        cursor = await db.execute(
            "SELECT owner_id FROM clients WHERE id = ? AND guild_id = ?",
            (client_id, guild_id),
        )
        row = await cursor.fetchone()
        if not row or row["owner_id"] != owner_id:
            return None

        cursor = await db.execute(
            "SELECT * FROM client_followups WHERE client_id = ? ORDER BY created_at DESC",
            (client_id,),
        )
        rows = await cursor.fetchall()
        return [ClientFollowup(**dict(row)) for row in rows]


async def get_client(*, client_id: int, guild_id: int, owner_id: int) -> Optional[Client]:
    async with database.connect() as db:
        cursor = await db.execute(
            "SELECT * FROM clients WHERE id = ? AND guild_id = ? AND owner_id = ?",
            (client_id, guild_id, owner_id),
        )
        row = await cursor.fetchone()
        return Client(**dict(row)) if row else None
