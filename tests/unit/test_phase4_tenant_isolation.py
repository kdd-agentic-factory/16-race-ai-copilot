from __future__ import annotations

import asyncio

from sqlalchemy import text

from race_ai_copilot.conversation_store import engine, init_conversation_db, load_history, save_turn


async def _clear_conversations() -> None:
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM conversation_turns"))


def test_conversation_history_is_scoped_by_tenant_id():
    asyncio.run(init_conversation_db())
    asyncio.run(_clear_conversations())

    asyncio.run(
        save_turn(
            conversation_id="conv-tenant-shared",
            tenant_id="tenant-a",
            role="user",
            content="tenant-a hello",
            session_id="session-a",
        )
    )
    asyncio.run(
        save_turn(
            conversation_id="conv-tenant-shared",
            tenant_id="tenant-b",
            role="user",
            content="tenant-b hello",
            session_id="session-b",
        )
    )

    tenant_a_history = asyncio.run(load_history("conv-tenant-shared", tenant_id="tenant-a"))
    tenant_b_history = asyncio.run(load_history("conv-tenant-shared", tenant_id="tenant-b"))

    assert [turn["content"] for turn in tenant_a_history] == ["tenant-a hello"]
    assert [turn["content"] for turn in tenant_b_history] == ["tenant-b hello"]
