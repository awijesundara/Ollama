import hashlib
import json
import logging
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

import asyncpg

logger = logging.getLogger("memory.audit")


def hash_user_identifier(identifier: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{identifier}".encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class AuditEvent:
    user_identifier: str
    operation: str
    actor: str = "user"
    memory_id: UUID | None = None
    scope: str | None = None
    thread_id: str | None = None
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class AuditRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def record(self, event: AuditEvent) -> None:
        await self._pool.execute(
            """
            INSERT INTO memory_audit_events (
                user_identifier, memory_id, operation, scope, thread_id,
                actor, reason, metadata
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb)
            """,
            event.user_identifier,
            event.memory_id,
            event.operation,
            event.scope,
            event.thread_id,
            event.actor,
            event.reason,
            json.dumps(event.metadata),
        )

    async def purge(self, retention_days: int) -> int:
        result = await self._pool.execute(
            """
            DELETE FROM memory_audit_events
            WHERE created_at < NOW() - make_interval(days => $1)
            """,
            retention_days,
        )
        return int(result.rsplit(" ", 1)[-1])
