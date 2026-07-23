from uuid import UUID

from src.auth.identity import AuthenticatedIdentity
from src.memory.models import (
    MemoryCreate,
    MemoryPreferences,
    MemoryPreferenceUpdate,
    MemoryRecord,
    MemoryScope,
    RetrievedMemory,
)
from src.memory.repository import MemoryRepository
from src.memory.validator import MemoryValidator


class MemoryDisabledError(RuntimeError):
    pass


class MemoryService:
    def __init__(
        self,
        repository: MemoryRepository,
        validator: MemoryValidator,
        *,
        max_items_per_user: int = 500,
        max_global_results: int = 10,
        max_thread_results: int = 10,
    ) -> None:
        self._repository = repository
        self._validator = validator
        self._max_items = max_items_per_user
        self._max_global = max_global_results
        self._max_thread = max_thread_results

    async def create_memory(
        self,
        identity: AuthenticatedIdentity,
        request: MemoryCreate,
    ) -> MemoryRecord:
        preferences = await self._repository.get_preferences(identity.user_identifier)
        if request.scope is MemoryScope.GLOBAL and not preferences.allow_global_memory:
            raise MemoryDisabledError("Global memory is disabled")
        if request.scope is MemoryScope.THREAD and not preferences.allow_thread_memory:
            raise MemoryDisabledError("Thread memory is disabled")
        validated = self._validator.validate(request)
        return await self._repository.create(
            identity.user_identifier,
            validated,
            scope=request.scope,
            thread_id=request.thread_id,
            category=request.category,
            importance=request.importance,
            confidence=request.confidence,
            source=request.source,
            source_message_id=request.source_message_id,
            max_items=self._max_items,
        )

    async def retrieve_for_prompt(
        self,
        identity: AuthenticatedIdentity,
        thread_id: str,
        query: str,
    ) -> RetrievedMemory:
        del query  # Phase 1 uses importance/recency retrieval.
        preferences = await self._repository.get_preferences(identity.user_identifier)
        if not preferences.memory_enabled:
            return RetrievedMemory()
        global_memories = (
            await self._repository.list_active(
                identity.user_identifier,
                scope=MemoryScope.GLOBAL,
                limit=self._max_global,
            )
            if preferences.allow_global_memory
            else []
        )
        thread_memories = (
            await self._repository.list_active(
                identity.user_identifier,
                scope=MemoryScope.THREAD,
                thread_id=thread_id,
                limit=self._max_thread,
            )
            if preferences.allow_thread_memory
            else []
        )
        return RetrievedMemory(
            global_memories=global_memories,
            thread_memories=thread_memories,
        )

    async def list_memories(
        self,
        identity: AuthenticatedIdentity,
        scope: MemoryScope | None = None,
        thread_id: str | None = None,
    ) -> list[MemoryRecord]:
        return await self._repository.list_active(
            identity.user_identifier,
            scope=scope,
            thread_id=thread_id,
        )

    async def delete_memory(
        self,
        identity: AuthenticatedIdentity,
        memory_id: UUID,
    ) -> bool:
        return await self._repository.delete(identity.user_identifier, memory_id)

    async def delete_all_global(self, identity: AuthenticatedIdentity) -> int:
        return await self._repository.delete_all(
            identity.user_identifier,
            scope=MemoryScope.GLOBAL,
            thread_id=None,
        )

    async def delete_all_thread(
        self,
        identity: AuthenticatedIdentity,
        thread_id: str,
    ) -> int:
        return await self._repository.delete_all(
            identity.user_identifier,
            scope=MemoryScope.THREAD,
            thread_id=thread_id,
        )

    async def update_preferences(
        self,
        identity: AuthenticatedIdentity,
        update: MemoryPreferenceUpdate,
    ) -> MemoryPreferences:
        return await self._repository.update_preferences(
            identity.user_identifier,
            update,
        )
