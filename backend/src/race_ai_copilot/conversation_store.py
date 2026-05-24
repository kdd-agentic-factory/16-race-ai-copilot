"""Async conversation history store — PostgreSQL in production, SQLite for local dev."""

import json
import logging
import os
from typing import Dict, List

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool

logger = logging.getLogger(__name__)

_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./copilot_conversations.db",
)
if _DATABASE_URL.startswith("postgresql://"):
    _DATABASE_URL = _DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
elif _DATABASE_URL.startswith("postgres://"):
    _DATABASE_URL = _DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)

_is_sqlite = _DATABASE_URL.startswith("sqlite")

engine = create_async_engine(
    _DATABASE_URL,
    echo=False,
    poolclass=NullPool if _is_sqlite else AsyncAdaptedQueuePool,
    pool_pre_ping=not _is_sqlite,
)
_SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

_DDL = """
CREATE TABLE IF NOT EXISTS conversation_turns (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    session_id      TEXT,
    role            TEXT NOT NULL,
    content         TEXT NOT NULL,
    metadata        TEXT NOT NULL DEFAULT '{}',
    created_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_conv_id ON conversation_turns (conversation_id);
"""

# Postgres-compatible DDL (no AUTOINCREMENT keyword)
_DDL_PG = """
CREATE TABLE IF NOT EXISTS conversation_turns (
    id              BIGSERIAL PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    session_id      TEXT,
    role            TEXT NOT NULL,
    content         TEXT NOT NULL,
    metadata        JSONB NOT NULL DEFAULT '{}',
    created_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_conv_id ON conversation_turns (conversation_id);
"""


async def init_conversation_db() -> None:
    ddl = _DDL_PG if not _is_sqlite else _DDL
    async with engine.begin() as conn:
        for stmt in ddl.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                await conn.execute(text(stmt))
    logger.info("Conversation DB ready (%s)", "sqlite" if _is_sqlite else "postgres")


async def save_turn(
    conversation_id: str,
    role: str,
    content: str,
    session_id: str = None,
    metadata: Dict = None,
    created_at: str = None,
) -> None:
    from datetime import datetime, timezone
    ts = created_at or datetime.now(timezone.utc).isoformat()
    meta_str = json.dumps(metadata or {})
    async with _SessionLocal() as db:
        await db.execute(
            text("""
                INSERT INTO conversation_turns
                    (conversation_id, session_id, role, content, metadata, created_at)
                VALUES
                    (:conv_id, :session_id, :role, :content, :meta, :ts)
            """),
            {
                "conv_id": conversation_id,
                "session_id": session_id,
                "role": role,
                "content": content,
                "meta": meta_str,
                "ts": ts,
            },
        )
        await db.commit()


async def load_history(conversation_id: str, max_turns: int = 20) -> List[Dict[str, str]]:
    """Return the last ``max_turns`` turns as a list of {role, content} dicts."""
    async with _SessionLocal() as db:
        result = await db.execute(
            text("""
                SELECT role, content FROM conversation_turns
                WHERE conversation_id = :conv_id
                ORDER BY id DESC
                LIMIT :limit
            """),
            {"conv_id": conversation_id, "limit": max_turns},
        )
        rows = result.fetchall()
    # Reverse to get chronological order
    return [{"role": r.role, "content": r.content} for r in reversed(rows)]
