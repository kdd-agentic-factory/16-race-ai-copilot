"""Integration test fixtures — initialise the SQLite conversation DB once per session."""
import asyncio
import os

import pytest


@pytest.fixture(scope="session", autouse=True)
def _init_db():
    from race_ai_copilot.conversation_store import init_conversation_db
    asyncio.run(init_conversation_db())
