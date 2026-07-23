import asyncio
import os
from uuid import uuid4

import asyncpg
import pytest

from src.memory.models import MemoryScope, MemorySource
from src.memory.repository import PostgresMemoryRepository
from src.memory.validator import ValidatedMemory

pytestmark = pytest.mark.integration


@pytest.fixture
async def repository() -> PostgresMemoryRepository:
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is not configured")
    pool = await asyncpg.create_pool(url)
    try:
        yield PostgresMemoryRepository(pool)
    finally:
        await pool.close()


@pytest.mark.asyncio
async def test_cross_user_list_and_delete_are_isolated(
    repository: PostgresMemoryRepository,
) -> None:
    alice = f"alice-{uuid4()}"
    bob = f"bob-{uuid4()}"
    normalized = f"alice fact {uuid4()}"
    record = await repository.create(
        alice,
        ValidatedMemory(
            display_text=normalized,
            normalized_text=normalized,
            normalized_hash="a" * 64,
        ),
        scope=MemoryScope.GLOBAL,
        thread_id=None,
        category="test",
        importance=5,
        confidence=1,
        source=MemorySource.EXPLICIT,
        source_message_id=None,
        expires_at=None,
        max_items=500,
    )
    assert await repository.list_active(bob) == []
    assert await repository.delete(bob, record.id) is False
    assert await repository.list_active(alice) == [record]


@pytest.mark.asyncio
async def test_thread_memory_does_not_cross_threads(
    repository: PostgresMemoryRepository,
) -> None:
    user = f"user-{uuid4()}"
    text = f"thread fact {uuid4()}"
    await repository.create(
        user,
        ValidatedMemory(
            display_text=text,
            normalized_text=text,
            normalized_hash="b" * 64,
        ),
        scope=MemoryScope.THREAD,
        thread_id="thread-a",
        category="test",
        importance=5,
        confidence=1,
        source=MemorySource.EXPLICIT,
        source_message_id=None,
        expires_at=None,
        max_items=500,
    )
    assert len(
        await repository.list_active(
            user, scope=MemoryScope.THREAD, thread_id="thread-a"
        )
    ) == 1
    assert (
        await repository.list_active(
            user, scope=MemoryScope.THREAD, thread_id="thread-b"
        )
        == []
    )


@pytest.mark.asyncio
async def test_concurrent_duplicate_insert_keeps_one_record(
    repository: PostgresMemoryRepository,
) -> None:
    user = f"duplicate-{uuid4()}"
    text = f"same fact {uuid4()}"
    memory = ValidatedMemory(
        display_text=text,
        normalized_text=text,
        normalized_hash="c" * 64,
    )

    async def create() -> object:
        return await repository.create(
            user,
            memory,
            scope=MemoryScope.GLOBAL,
            thread_id=None,
            category="test",
            importance=5,
            confidence=1,
            source=MemorySource.EXPLICIT,
            source_message_id=None,
            expires_at=None,
            max_items=500,
        )

    results = await asyncio.gather(create(), create(), return_exceptions=True)
    assert sum(not isinstance(result, Exception) for result in results) == 1
    assert len(await repository.list_active(user)) == 1


@pytest.mark.asyncio
async def test_constraint_failure_does_not_leave_partial_row(
    repository: PostgresMemoryRepository,
) -> None:
    user = f"rollback-{uuid4()}"
    text = f"invalid fact {uuid4()}"
    with pytest.raises(asyncpg.CheckViolationError):
        await repository.create(
            user,
            ValidatedMemory(
                display_text=text,
                normalized_text=text,
                normalized_hash="d" * 64,
            ),
            scope=MemoryScope.GLOBAL,
            thread_id=None,
            category="test",
            importance=99,
            confidence=1,
            source=MemorySource.EXPLICIT,
            source_message_id=None,
            expires_at=None,
            max_items=500,
        )
    assert await repository.list_active(user) == []
