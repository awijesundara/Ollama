from datetime import UTC, datetime, timedelta

from src.security.audit import AuditEvent
from src.storage.encrypted_store import Document, EncryptedUserStore


class EncryptedFileAuditRepository:
    def __init__(self, store: EncryptedUserStore) -> None:
        self._store = store

    async def record(self, event: AuditEvent) -> None:
        def append(document: Document) -> None:
            document["audits"].append(
                {
                    "user_identifier": event.user_identifier,
                    "memory_id": str(event.memory_id) if event.memory_id else None,
                    "operation": event.operation,
                    "scope": event.scope,
                    "thread_id": event.thread_id,
                    "actor": event.actor,
                    "reason": event.reason,
                    "metadata": event.metadata,
                    "created_at": datetime.now(UTC).isoformat(),
                }
            )

        await self._store.mutate_user(event.user_identifier, append)

    async def purge(self, retention_days: int) -> int:
        cutoff = datetime.now(UTC) - timedelta(days=retention_days)
        removed = 0
        for identifier in await self._store.all_user_identifiers():

            def purge_user(document: Document) -> int:
                previous = len(document["audits"])
                document["audits"] = [
                    event
                    for event in document["audits"]
                    if datetime.fromisoformat(event["created_at"]) >= cutoff
                ]
                return previous - len(document["audits"])

            removed += await self._store.mutate_user(identifier, purge_user)
        return removed
