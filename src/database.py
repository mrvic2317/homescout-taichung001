"""Async SQLite database helper for VicBot."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

import aiosqlite

_DB_PATH = Path("vicbot.db")


async def init_db() -> None:
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON;")
        await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS monitoring (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                guild_id INTEGER NOT NULL,
                area TEXT NOT NULL,
                price_min INTEGER,
                price_max INTEGER,
                size_min REAL,
                size_max REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                creator_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                area TEXT,
                price INTEGER,
                status TEXT NOT NULL,
                assignee_id INTEGER,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TRIGGER IF NOT EXISTS trg_cases_updated_at
            AFTER UPDATE ON cases
            FOR EACH ROW
            BEGIN
                UPDATE cases SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END;

            CREATE TABLE IF NOT EXISTS case_updates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL,
                status TEXT,
                note TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                owner_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                budget_min INTEGER,
                budget_max INTEGER,
                preferred_areas TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TRIGGER IF NOT EXISTS trg_clients_updated_at
            AFTER UPDATE ON clients
            FOR EACH ROW
            BEGIN
                UPDATE clients SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END;

            CREATE TABLE IF NOT EXISTS client_followups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL,
                note TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS viewings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                creator_id INTEGER NOT NULL,
                scheduled_at TIMESTAMP NOT NULL,
                client TEXT NOT NULL,
                property TEXT NOT NULL,
                agent TEXT,
                contact TEXT,
                note TEXT,
                link TEXT,
                reminded INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        await db.commit()


@asynccontextmanager
async def connect() -> AsyncIterator[aiosqlite.Connection]:
    db = await aiosqlite.connect(_DB_PATH)
    try:
        await db.execute("PRAGMA foreign_keys = ON;")
        db.row_factory = aiosqlite.Row
        yield db
    finally:
        await db.close()


def run_sync(coro):
    return asyncio.get_event_loop().run_until_complete(coro)
