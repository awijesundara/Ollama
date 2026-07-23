from src.auth.identity import AuthenticatedIdentity
from src.memory.conflicts import ConflictDetector
from src.memory.models import (
    ExtractionResult,
    MemoryCreate,
    MemoryScope,
    MemorySource,
)
from src.memory.service import MemoryService
from src.memory.validator import MemoryValidationError
from src.ollama.client import OllamaService
from src.ollama.models import ChatMessage
from src.security.audit import AuditEvent, AuditRepository


EXTRACTION_POLICY = """Extract only durable user-provided preferences, role
information, regular technical environment details, long-term project decisions,
communication preferences, or explicit requests to remember. Never save credentials,
health, HR, salary, legal, disputes, third-party facts, incidents, guesses, or
assistant conclusions. Return schema-valid candidates."""


class MemoryExtractor:
    def __init__(
        self,
        ollama: OllamaService,
        memory_service: MemoryService,
        minimum_importance: int,
        minimum_confidence: float = 0.85,
        conflict_detector: ConflictDetector | None = None,
        retention_days: int = 365,
        create_embeddings: bool = False,
        audit: AuditRepository | None = None,
        embedding_dimensions: int = 768,
    ) -> None:
        self._ollama = ollama
        self._memory_service = memory_service
        self._importance = minimum_importance
        self._confidence = minimum_confidence
        self._conflicts = conflict_detector
        self._retention_days = retention_days
        self._create_embeddings = create_embeddings
        self._audit = audit
        self._embedding_dimensions = embedding_dimensions

    async def extract(
        self,
        identity: AuthenticatedIdentity,
        user_message: str,
        thread_id: str,
        source_message_id: str | None,
    ) -> int:
        result = await self._ollama.structured_chat(
            [
                ChatMessage(role="system", content=EXTRACTION_POLICY),
                ChatMessage(role="user", content=user_message),
            ],
            ExtractionResult,
        )
        saved = 0
        for candidate in result.candidates:
            if (
                not candidate.save
                or candidate.importance < self._importance
                or candidate.confidence < self._confidence
            ):
                continue
            request = MemoryCreate(
                text=candidate.memory,
                scope=candidate.scope,
                thread_id=(
                    thread_id if candidate.scope is MemoryScope.THREAD else None
                ),
                category=candidate.category,
                importance=candidate.importance,
                confidence=candidate.confidence,
                source=MemorySource.AUTOMATIC,
                source_message_id=source_message_id,
                expires_at=datetime.now(UTC)
                + timedelta(days=self._retention_days),
            )
            try:
                if self._conflicts:
                    conflict = await self._conflicts.find(identity, request)
                    if conflict.conflicts:
                        continue
                record = await self._memory_service.create_memory(identity, request)
                if self._create_embeddings:
                    try:
                        embedding = await self._ollama.create_embedding(record.text)
                        if len(embedding) == self._embedding_dimensions:
                            await self._memory_service.attach_embedding(
                                identity, record.id, embedding
                            )
                    except RuntimeError:
                        pass
                if self._audit:
                    await self._audit.record(
                        AuditEvent(
                            user_identifier=identity.user_identifier,
                            memory_id=record.id,
                            operation="create",
                            scope=record.scope.value,
                            thread_id=record.thread_id,
                            actor="automatic",
                        )
                    )
                saved += 1
            except MemoryValidationError as error:
                if self._audit:
                    await self._audit.record(
                        AuditEvent(
                            user_identifier=identity.user_identifier,
                            operation="reject",
                            actor="automatic",
                            reason=error.reason,
                        )
                    )
                continue
            except RuntimeError:
                continue
        return saved
from datetime import UTC, datetime, timedelta
