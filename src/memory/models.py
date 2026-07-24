from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MemoryScope(StrEnum):
    GLOBAL = "global"
    THREAD = "thread"


class MemorySource(StrEnum):
    EXPLICIT = "explicit"
    AUTOMATIC = "automatic"
    ADMIN = "admin"


class MemoryCreate(BaseModel):
    text: str
    scope: MemoryScope
    thread_id: str | None = None
    category: str = "general"
    importance: int = Field(default=5, ge=1, le=10)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source: MemorySource = MemorySource.EXPLICIT
    source_message_id: str | None = None
    expires_at: datetime | None = None

    @model_validator(mode="after")
    def validate_scope(self) -> "MemoryCreate":
        if self.scope is MemoryScope.THREAD and not self.thread_id:
            raise ValueError("Thread memory requires a thread_id")
        if self.scope is MemoryScope.GLOBAL and self.thread_id is not None:
            raise ValueError("Global memory cannot have a thread_id")
        return self


class MemoryRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_identifier: str
    text: str
    scope: MemoryScope
    thread_id: str | None
    category: str
    importance: int
    confidence: float
    source: MemorySource
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None = None


class MemoryPreferences(BaseModel):
    user_identifier: str
    memory_enabled: bool = True
    automatic_memory_enabled: bool = True
    allow_global_memory: bool = True
    allow_thread_memory: bool = True


class MemoryPreferenceUpdate(BaseModel):
    memory_enabled: bool | None = None
    automatic_memory_enabled: bool | None = None
    allow_global_memory: bool | None = None
    allow_thread_memory: bool | None = None


class RetrievedMemory(BaseModel):
    global_memories: list[MemoryRecord] = Field(default_factory=list)
    thread_memories: list[MemoryRecord] = Field(default_factory=list)


class MemoryExport(BaseModel):
    exported_at: datetime
    user_identifier: str
    preferences: MemoryPreferences
    memories: list[MemoryRecord]


class ExtractionCandidate(BaseModel):
    save: bool
    scope: MemoryScope
    category: str = "general"
    memory: str
    importance: int = Field(ge=1, le=10)
    confidence: float = Field(ge=0, le=1)
    reason: str


class ExtractionResult(BaseModel):
    candidates: list[ExtractionCandidate] = Field(default_factory=list, max_length=20)


class ConflictAssessment(BaseModel):
    conflicts: bool
    conflicting_memory_id: UUID | None = None
    reason: str = ""

    @model_validator(mode="after")
    def require_id_for_conflict(self) -> "ConflictAssessment":
        if self.conflicts and self.conflicting_memory_id is None:
            raise ValueError("A conflicting memory ID is required")
        return self
