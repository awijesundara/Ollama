import asyncio
import json
from datetime import UTC, datetime, timedelta

from src.runtime import services
from src.storage.encrypted_store import Document


async def main() -> None:
    await services.start()
    try:
        audits = (
            await services.audit.purge(services.settings.AUDIT_RETENTION_DAYS)
            if services.audit
            else 0
        )
        if services.file_store is not None:
            expired_count = 0
            thread_count = 0
            now = datetime.now(UTC)
            for identifier in await services.file_store.all_user_identifiers():

                def retain(document: Document) -> None:
                    nonlocal expired_count, thread_count
                    for memory in document["memories"]:
                        expires = memory.get("expires_at")
                        if (
                            memory.get("deleted_at") is None
                            and isinstance(expires, str)
                            and datetime.fromisoformat(expires) <= now
                        ):
                            memory["deleted_at"] = now.isoformat()
                            expired_count += 1
                    cutoff = now - timedelta(
                        days=services.settings.THREAD_RETENTION_DAYS
                    )
                    stale = [
                        thread_id
                        for thread_id, thread in document["threads"].items()
                        if datetime.fromisoformat(
                            thread.get("updatedAt") or thread["createdAt"]
                        )
                        < cutoff
                    ]
                    for thread_id in stale:
                        document["threads"].pop(thread_id, None)
                        document["summaries"].pop(thread_id, None)
                    thread_count += len(stale)

                await services.file_store.mutate_user(identifier, retain)
        else:
            expired = await services.database.pool.execute(
                """
                UPDATE user_memories
                SET deleted_at = NOW(), updated_at = NOW()
                WHERE deleted_at IS NULL AND expires_at <= NOW()
                """
            )
            expired_count = int(expired.rsplit(" ", 1)[-1])
            threads = await services.database.pool.execute(
                """
                DELETE FROM threads
                WHERE "createdAt" ~ '^\\d{4}-\\d{2}-\\d{2}T'
                  AND "createdAt"::timestamptz
                        < NOW() - make_interval(days => $1)
                """,
                services.settings.THREAD_RETENTION_DAYS,
            )
            thread_count = int(threads.rsplit(" ", 1)[-1])
        print(
            json.dumps(
                {
                    "expired_memories": expired_count,
                    "deleted_audits": audits,
                    "abandoned_threads": thread_count,
                }
            )
        )
    finally:
        if services.settings.STORAGE_BACKEND == "postgresql":
            await services.database.close()
        await services.ollama.close()


if __name__ == "__main__":
    asyncio.run(main())
