from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest

from src.auth.identity import AuthenticatedIdentity
from src.memory.models import (
    MemoryCreate,
    MemoryPreferences,
    MemoryPreferenceUpdate,
    MemoryRecord,
    MemoryScope,
    MemorySource,
)
from src.memory.service import MemoryService
from src.memory.validator import MemoryValidator, ValidatedMemory


class FakeRepository:
    def __init__(self) -> None:
        self.records: dict[UUID, MemoryRecord] = {}
        self.seen_owners: list[str] = []

    async def create(
        self,
        user_identifier: str,
        memory: ValidatedMemory,
        **values: Any,
    ) -> MemoryRecord:
        self.seen_owners.append(user_identifier)
        now = datetime.now(UTC)
        record = MemoryRecord(
            id=uuid4(),
            user_identifier=user_identifier,
            text=memory.display_text,
            scope=values["scope"],
            thread_id=values["thread_id"],
            category=values["category"],
            importance=values["importance"],
            confidence=values["confidence"],
            source=values["source"],
            created_at=now,
            updated_at=now,
        )
        self.records[record.id] = record
        return record

    async def list_active(
        self,
        user_identifier: str,
        *,
        scope: MemoryScope | None = None,
        thread_id: str | None = None,
        limit: int | None = None,
    ) -> list[MemoryRecord]:
        self.seen_owners.append(user_identifier)
        result = [
            item
            for item in self.records.values()
            if item.user_identifier == user_identifier
            and (scope is None or item.scope is scope)
            and (thread_id is None or item.thread_id == thread_id)
        ]
        return result[:limit]

    async def delete(self, user_identifier: str, memory_id: UUID) -> bool:
        self.seen_owners.append(user_identifier)
        item = self.records.get(memory_id)
        if item is None or item.user_identifier != user_identifier:
            return False
        del self.records[memory_id]
        return True

    async def delete_all(
        self,
        user_identifier: str,
        *,
        scope: MemoryScope,
        thread_id: str | None,
    ) -> int:
        matching = [
            memory_id
            for memory_id, item in self.records.items()
            if item.user_identifier == user_identifier
            and item.scope is scope
            and (thread_id is None or item.thread_id == thread_id)
        ]
        for memory_id in matching:
            del self.records[memory_id]
        return len(matching)

    async def get_preferences(self, user_identifier: str) -> MemoryPreferences:
        self.seen_owners.append(user_identifier)
        return MemoryPreferences(user_identifier=user_identifier)

    async def update_preferences(
        self,
        user_identifier: str,
        update: MemoryPreferenceUpdate,
    ) -> MemoryPreferences:
        return MemoryPreferences(
            user_identifier=user_identifier,
            **update.model_dump(exclude_none=True),
        )


@pytest.mark.asyncio
async def test_user_cannot_list_or_delete_another_users_memory() -> None:
    repository = FakeRepository()
    service = MemoryService(repository, MemoryValidator(500))
    alice = AuthenticatedIdentity("alice-guid")
    bob = AuthenticatedIdentity("bob-guid")
    created = await service.create_memory(
        alice,
        MemoryCreate(
            text="Alice prefers Rocky Linux",
            scope=MemoryScope.GLOBAL,
            source=MemorySource.EXPLICIT,
        ),
    )

    assert await service.list_memories(bob) == []
    assert await service.delete_memory(bob, created.id) is False
    assert await service.list_memories(alice) == [created]
    assert "alice-guid" in repository.seen_owners
    assert "bob-guid" in repository.seen_owners


@pytest.mark.asyncio
async def test_thread_memory_is_retrieved_only_for_its_thread() -> None:
    repository = FakeRepository()
    service = MemoryService(repository, MemoryValidator(500))
    alice = AuthenticatedIdentity("alice-guid")
    await service.create_memory(
        alice,
        MemoryCreate(
            text="This project uses PostgreSQL 16",
            scope=MemoryScope.THREAD,
            thread_id="project-a",
            source=MemorySource.EXPLICIT,
        ),
    )

    project_a = await service.retrieve_for_prompt(alice, "project-a", "database?")
    project_b = await service.retrieve_for_prompt(alice, "project-b", "database?")
    assert len(project_a.thread_memories) == 1
    assert project_b.thread_memories == []
