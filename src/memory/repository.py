from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

import asyncpg

from src.memory.models import (
    MemoryPreferences,
    MemoryPreferenceUpdate,
    MemoryRecord,
    MemoryScope,
    MemorySource,
)
from src.memory.validator import ValidatedMemory


class DuplicateMemoryError(RuntimeError):
    pass


class MemoryLimitError(RuntimeError):
    pass


class RepositoryError(RuntimeError):
    pass


class MemoryRepository(Protocol):
    async def create(
        self,
        user_identifier: str,
        memory: ValidatedMemory,
        *,
        scope: MemoryScope,
        thread_id: str | None,
        category: str,
        importance: int,
        confidence: float,
        source: MemorySource,
        source_message_id: str | None,
        max_items: int,
    ) -> MemoryRecord: ...

    async def list_active(
        self,
        user_identifier: str,
        *,
        scope: MemoryScope | None = None,
        thread_id: str | None = None,
        limit: int | None = None,
    ) -> list[MemoryRecord]: ...

    async def delete(self, user_identifier: str, memory_id: UUID) -> bool: ...

    async def delete_all(
        self,
        user_identifier: str,
        *,
        scope: MemoryScope,
        thread_id: str | None,
    ) -> int: ...

    async def get_preferences(self, user_identifier: str) -> MemoryPreferences: ...

    async def update_preferences(
        self,
        user_identifier: str,
        update: MemoryPreferenceUpdate,
    ) -> MemoryPreferences: ...


class PostgresMemoryRepository:
    """Parameterised PostgreSQL operations with mandatory ownership filters."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create(
        self,
        user_identifier: str,
        memory: ValidatedMemory,
        *,
        scope: MemoryScope,
        thread_id: str | None,
        category: str,
        importance: int,
        confidence: float,
        source: MemorySource,
        source_message_id: str | None,
        max_items: int,
    ) -> MemoryRecord:
        query = """
            WITH item_count AS (
                SELECT count(*) AS count
                FROM user_memories
                WHERE user_identifier = $1 AND deleted_at IS NULL
            )
            INSERT INTO user_memories (
                user_identifier, scope, thread_id, category, memory_text,
                normalized_text, normalized_hash, importance, confidence,
                source, source_message_id
            )
            SELECT $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11
            FROM item_count
            WHERE item_count.count < $12
            RETURNING id, user_identifier, memory_text AS text, scope, thread_id,
                      category, importance, confidence::float8 AS confidence,
                      source, created_at, updated_at
        """
        try:
            row = await self._pool.fetchrow(
                query,
                user_identifier,
                scope.value,
                thread_id,
                category,
                memory.display_text,
                memory.normalized_text,
                memory.normalized_hash,
                importance,
                confidence,
                source.value,
                source_message_id,
                max_items,
            )
        except asyncpg.UniqueViolationError as error:
            raise DuplicateMemoryError("Memory already exists") from error
        if row is None:
            raise MemoryLimitError("Per-user memory limit reached")
        return _record(row)

    async def list_active(
        self,
        user_identifier: str,
        *,
        scope: MemoryScope | None = None,
        thread_id: str | None = None,
        limit: int | None = None,
    ) -> list[MemoryRecord]:
        query = """
            SELECT id, user_identifier, memory_text AS text, scope, thread_id,
                   category, importance, confidence::float8 AS confidence,
                   source, created_at, updated_at
            FROM user_memories
            WHERE user_identifier = $1
              AND deleted_at IS NULL
              AND (expires_at IS NULL OR expires_at > NOW())
              AND ($2::text IS NULL OR scope = $2)
              AND ($3::text IS NULL OR thread_id = $3)
            ORDER BY importance DESC, last_used_at DESC NULLS LAST, updated_at DESC
            LIMIT COALESCE($4, 2147483647)
        """
        rows = await self._pool.fetch(
            query,
            user_identifier,
            scope.value if scope else None,
            thread_id,
            limit,
        )
        return [_record(row) for row in rows]

    async def delete(self, user_identifier: str, memory_id: UUID) -> bool:
        result = await self._pool.execute(
            """
            UPDATE user_memories SET deleted_at = NOW(), updated_at = NOW()
            WHERE id = $1 AND user_identifier = $2 AND deleted_at IS NULL
            """,
            memory_id,
            user_identifier,
        )
        return bool(result == "UPDATE 1")

    async def delete_all(
        self,
        user_identifier: str,
        *,
        scope: MemoryScope,
        thread_id: str | None,
    ) -> int:
        result = await self._pool.execute(
            """
            UPDATE user_memories SET deleted_at = NOW(), updated_at = NOW()
            WHERE user_identifier = $1 AND scope = $2
              AND ($3::text IS NULL OR thread_id = $3)
              AND deleted_at IS NULL
            """,
            user_identifier,
            scope.value,
            thread_id,
        )
        return int(result.rsplit(" ", 1)[-1])

    async def get_preferences(self, user_identifier: str) -> MemoryPreferences:
        row = await self._pool.fetchrow(
            """
            INSERT INTO user_memory_preferences (user_identifier)
            VALUES ($1)
            ON CONFLICT (user_identifier) DO UPDATE
                SET user_identifier = EXCLUDED.user_identifier
            RETURNING *
            """,
            user_identifier,
        )
        if row is None:
            raise RepositoryError("Preference creation returned no row")
        return MemoryPreferences.model_validate(dict(row))

    async def update_preferences(
        self,
        user_identifier: str,
        update: MemoryPreferenceUpdate,
    ) -> MemoryPreferences:
        current = await self.get_preferences(user_identifier)
        values = current.model_copy(update=update.model_dump(exclude_none=True))
        row = await self._pool.fetchrow(
            """
            UPDATE user_memory_preferences
            SET memory_enabled = $2, automatic_memory_enabled = $3,
                allow_global_memory = $4, allow_thread_memory = $5,
                updated_at = NOW()
            WHERE user_identifier = $1
            RETURNING *
            """,
            user_identifier,
            values.memory_enabled,
            values.automatic_memory_enabled,
            values.allow_global_memory,
            values.allow_thread_memory,
        )
        if row is None:
            raise RepositoryError("Preference update returned no row")
        return MemoryPreferences.model_validate(dict(row))


def _record(row: Sequence[object]) -> MemoryRecord:
    return MemoryRecord.model_validate(dict(row))  # type: ignore[arg-type]
