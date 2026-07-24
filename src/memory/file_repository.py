import math
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.memory.models import (
    MemoryPreferences,
    MemoryPreferenceUpdate,
    MemoryRecord,
    MemoryScope,
    MemorySource,
)
from src.memory.repository import DuplicateMemoryError, MemoryLimitError
from src.memory.validator import ValidatedMemory
from src.storage.encrypted_store import Document, EncryptedUserStore


class EncryptedFileMemoryRepository:
    def __init__(self, store: EncryptedUserStore) -> None:
        self._store = store

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
        expires_at: datetime | None,
        max_items: int,
    ) -> MemoryRecord:
        now = datetime.now(UTC)

        def create(document: Document) -> dict[str, object]:
            active = [
                item for item in document["memories"] if item.get("deleted_at") is None
            ]
            if len(active) >= max_items:
                raise MemoryLimitError("Per-user memory limit reached")
            if any(
                item["scope"] == scope.value
                and item.get("thread_id") == thread_id
                and item["normalized_hash"] == memory.normalized_hash
                for item in active
            ):
                raise DuplicateMemoryError("Memory already exists")
            item: dict[str, object] = {
                "id": str(uuid4()),
                "user_identifier": user_identifier,
                "text": memory.display_text,
                "normalized_text": memory.normalized_text,
                "normalized_hash": memory.normalized_hash,
                "scope": scope.value,
                "thread_id": thread_id,
                "category": category,
                "importance": importance,
                "confidence": confidence,
                "source": source.value,
                "source_message_id": source_message_id,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
                "last_used_at": None,
                "expires_at": expires_at.isoformat() if expires_at else None,
                "deleted_at": None,
                "embedding": None,
            }
            document["memories"].append(item)
            return item

        item = await self._store.mutate_user(user_identifier, create)
        return _record(item)

    async def list_active(
        self,
        user_identifier: str,
        *,
        scope: MemoryScope | None = None,
        thread_id: str | None = None,
        limit: int | None = None,
    ) -> list[MemoryRecord]:
        now = datetime.now(UTC)
        document = await self._store.read_user(user_identifier)
        records = [
            _record(item)
            for item in document["memories"]
            if item.get("deleted_at") is None
            and not _expired(item.get("expires_at"), now)
            and (scope is None or item["scope"] == scope.value)
            and (thread_id is None or item.get("thread_id") == thread_id)
        ]
        records.sort(
            key=lambda record: (record.importance, record.updated_at),
            reverse=True,
        )
        return records[:limit] if limit is not None else records

    async def delete(self, user_identifier: str, memory_id: UUID) -> bool:
        now = datetime.now(UTC).isoformat()

        def delete(document: Document) -> bool:
            for item in document["memories"]:
                if item["id"] == str(memory_id) and item.get("deleted_at") is None:
                    item["deleted_at"] = now
                    item["updated_at"] = now
                    return True
            return False

        return await self._store.mutate_user(user_identifier, delete)

    async def resolve_id_prefix(
        self, user_identifier: str, memory_id_prefix: str
    ) -> UUID | None:
        if not 8 <= len(memory_id_prefix) <= 36:
            return None
        document = await self._store.read_user(user_identifier)
        matches = [
            item["id"]
            for item in document["memories"]
            if item.get("deleted_at") is None
            and str(item["id"]).startswith(memory_id_prefix.lower())
        ]
        return UUID(str(matches[0])) if len(matches) == 1 else None

    async def delete_all(
        self,
        user_identifier: str,
        *,
        scope: MemoryScope,
        thread_id: str | None,
    ) -> int:
        now = datetime.now(UTC).isoformat()

        def delete(document: Document) -> int:
            count = 0
            for item in document["memories"]:
                if (
                    item["scope"] == scope.value
                    and item.get("deleted_at") is None
                    and (thread_id is None or item.get("thread_id") == thread_id)
                ):
                    item["deleted_at"] = now
                    item["updated_at"] = now
                    count += 1
            return count

        return await self._store.mutate_user(user_identifier, delete)

    async def get_preferences(self, user_identifier: str) -> MemoryPreferences:
        document = await self._store.read_user(user_identifier)
        return MemoryPreferences.model_validate(
            {
                "user_identifier": user_identifier,
                **document["preferences"],
            }
        )

    async def update_preferences(
        self,
        user_identifier: str,
        update: MemoryPreferenceUpdate,
    ) -> MemoryPreferences:
        values = update.model_dump(exclude_none=True)

        def apply(document: Document) -> dict[str, object]:
            document["preferences"].update(values)
            return dict(document["preferences"])

        preferences = await self._store.mutate_user(user_identifier, apply)
        return MemoryPreferences.model_validate(
            {
                "user_identifier": user_identifier,
                **preferences,
            }
        )

    async def set_embedding(
        self, user_identifier: str, memory_id: UUID, embedding: list[float]
    ) -> bool:
        def set_value(document: Document) -> bool:
            for item in document["memories"]:
                if item["id"] == str(memory_id) and item.get("deleted_at") is None:
                    item["embedding"] = embedding
                    item["updated_at"] = datetime.now(UTC).isoformat()
                    return True
            return False

        return await self._store.mutate_user(user_identifier, set_value)

    async def semantic_active(
        self,
        user_identifier: str,
        thread_id: str,
        embedding: list[float],
        similarity_threshold: float,
        limit: int,
    ) -> list[MemoryRecord]:
        now = datetime.now(UTC)
        document = await self._store.read_user(user_identifier)
        scored: list[tuple[float, MemoryRecord]] = []
        for item in document["memories"]:
            stored = item.get("embedding")
            if (
                item.get("deleted_at") is not None
                or _expired(item.get("expires_at"), now)
                or not isinstance(stored, list)
                or not (
                    item["scope"] == MemoryScope.GLOBAL.value
                    or (
                        item["scope"] == MemoryScope.THREAD.value
                        and item.get("thread_id") == thread_id
                    )
                )
            ):
                continue
            similarity = _cosine(embedding, [float(value) for value in stored])
            if similarity < similarity_threshold:
                continue
            record = _record(item)
            age = max(0.0, (now - record.updated_at).total_seconds())
            recency = max(0.0, 1.0 - age / 31_536_000)
            score = (
                similarity * 0.65
                + record.importance / 10 * 0.20
                + recency * 0.10
                + (0.05 if record.source is MemorySource.EXPLICIT else 0)
            )
            scored.append((score, record))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [record for _, record in scored[:limit]]

    async def mark_used(self, user_identifier: str, memory_ids: list[UUID]) -> None:
        wanted = {str(memory_id) for memory_id in memory_ids}
        if not wanted:
            return

        def mark(document: Document) -> None:
            now = datetime.now(UTC).isoformat()
            for item in document["memories"]:
                if item["id"] in wanted and item.get("deleted_at") is None:
                    item["last_used_at"] = now

        await self._store.mutate_user(user_identifier, mark)


def _record(item: dict[str, object]) -> MemoryRecord:
    return MemoryRecord.model_validate(item)


def _expired(value: object, now: datetime) -> bool:
    return isinstance(value, str) and datetime.fromisoformat(value) <= now


def _cosine(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        return -1.0
    numerator = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return -1.0
    return numerator / (left_norm * right_norm)
