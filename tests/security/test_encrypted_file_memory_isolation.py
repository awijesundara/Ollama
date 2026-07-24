import base64

import pytest

pytest.importorskip("cryptography")

from src.memory.file_repository import EncryptedFileMemoryRepository
from src.memory.models import MemoryScope, MemorySource
from src.memory.validator import ValidatedMemory
from src.storage.encrypted_store import EncryptedUserStore


@pytest.mark.asyncio
async def test_file_memory_queries_are_user_and_thread_scoped(tmp_path) -> None:
    key = base64.b64encode(b"s" * 32).decode()
    repository = EncryptedFileMemoryRepository(EncryptedUserStore(str(tmp_path), key))
    await repository.create(
        "alice",
        ValidatedMemory(
            display_text="PostgreSQL 16",
            normalized_text="postgresql 16",
            normalized_hash="f" * 64,
        ),
        scope=MemoryScope.THREAD,
        thread_id="project-a",
        category="technical",
        importance=7,
        confidence=1,
        source=MemorySource.EXPLICIT,
        source_message_id=None,
        expires_at=None,
        max_items=500,
    )

    assert await repository.list_active("bob") == []
    assert (
        await repository.list_active(
            "alice",
            scope=MemoryScope.THREAD,
            thread_id="project-b",
        )
        == []
    )
    assert (
        len(
            await repository.list_active(
                "alice",
                scope=MemoryScope.THREAD,
                thread_id="project-a",
            )
        )
        == 1
    )
