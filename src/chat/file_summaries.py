from datetime import UTC, datetime

from src.chat.models import ThreadSummary
from src.storage.encrypted_store import Document, EncryptedUserStore


class EncryptedFileThreadSummaryRepository:
    def __init__(self, store: EncryptedUserStore) -> None:
        self._store = store

    async def get(self, user_identifier: str, thread_id: str) -> ThreadSummary | None:
        document = await self._store.read_user(user_identifier)
        value = document["summaries"].get(thread_id)
        return ThreadSummary.model_validate(value) if value else None

    async def upsert(
        self,
        user_identifier: str,
        thread_id: str,
        summary: str,
        through_message_id: str | None,
        count: int,
    ) -> ThreadSummary:
        now = datetime.now(UTC)

        def upsert(document: Document) -> dict[str, object]:
            if thread_id not in document["threads"]:
                raise PermissionError("Thread summary ownership mismatch")
            previous = document["summaries"].get(thread_id, {})
            value: dict[str, object] = {
                "thread_id": thread_id,
                "user_identifier": user_identifier,
                "summary_text": summary,
                "summarized_through_message_id": through_message_id,
                "summarized_message_count": count,
                "created_at": previous.get("created_at", now.isoformat()),
                "updated_at": now.isoformat(),
            }
            document["summaries"][thread_id] = value
            return value

        return ThreadSummary.model_validate(
            await self._store.mutate_user(user_identifier, upsert)
        )
