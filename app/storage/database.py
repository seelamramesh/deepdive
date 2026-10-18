"""SQLite storage for research runs."""

from __future__ import annotations

import json
import aiosqlite
from typing import Optional

from app.models.schemas import ResearchRun

DB_PATH = "deepdive.db"


async def init_db() -> None:
    """Create tables if they don't exist."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY,
                question TEXT NOT NULL,
                created_at TEXT NOT NULL,
                current_state TEXT NOT NULL,
                data JSON NOT NULL
            )
        """)
        await db.commit()


async def save_run(run: ResearchRun) -> None:
    """Upsert a research run."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT OR REPLACE INTO runs (id, question, created_at, current_state, data)
               VALUES (?, ?, ?, ?, ?)""",
            (run.id, run.question, run.created_at, run.current_state.value,
             run.model_dump_json()),
        )
        await db.commit()


async def load_run(run_id: str) -> Optional[ResearchRun]:
    """Load a research run by ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT data FROM runs WHERE id = ?", (run_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            return ResearchRun.model_validate_json(row[0])


async def list_runs() -> list[dict]:
    """List all runs (summary only)."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, question, created_at, current_state FROM runs ORDER BY created_at DESC"
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                {"id": r[0], "question": r[1], "created_at": r[2], "state": r[3]}
                for r in rows
            ]
