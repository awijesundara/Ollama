import asyncio
import json

from src.runtime import services


async def main() -> None:
    await services.start()
    try:
        expired = await services.database.pool.execute(
            """
            UPDATE user_memories
            SET deleted_at = NOW(), updated_at = NOW()
            WHERE deleted_at IS NULL AND expires_at <= NOW()
            """
        )
        audits = (
            await services.audit.purge(services.settings.AUDIT_RETENTION_DAYS)
            if services.audit
            else 0
        )
        threads = await services.database.pool.execute(
            """
            DELETE FROM threads
            WHERE "createdAt" ~ '^\\d{4}-\\d{2}-\\d{2}T'
              AND "createdAt"::timestamptz
                    < NOW() - make_interval(days => $1)
            """,
            services.settings.THREAD_RETENTION_DAYS,
        )
        print(
            json.dumps(
                {
                    "expired_memories": int(expired.rsplit(" ", 1)[-1]),
                    "deleted_audits": audits,
                    "abandoned_threads": int(threads.rsplit(" ", 1)[-1]),
                }
            )
        )
    finally:
        await services.database.close()
        await services.ollama.close()


if __name__ == "__main__":
    asyncio.run(main())
