from dataclasses import dataclass

from src.auth.identity import AuthenticatedIdentity
from src.memory.models import RetrievedMemory
from src.memory.service import MemoryService
from src.ollama.client import OllamaService


@dataclass(slots=True)
class MemoryRetriever:
    service: MemoryService
    ollama: OllamaService | None = None
    semantic_enabled: bool = False
    similarity_threshold: float = 0.6
    limit: int = 20
    embedding_dimensions: int = 768

    async def retrieve(
        self,
        identity: AuthenticatedIdentity,
        thread_id: str,
        query: str,
    ) -> RetrievedMemory:
        # The service selects ownership/scope first. Embedding search can only
        # narrow this already authorized candidate set.
        memories = await self.service.retrieve_for_prompt(identity, thread_id, query)
        if self.ollama is None or not self.semantic_enabled:
            return memories
        # Embedding creation is intentionally best-effort; lexical Phase 1
        # retrieval remains available if Ollama embedding generation fails.
        try:
            embedding = await self.ollama.create_embedding(query)
        except RuntimeError:
            return memories
        if len(embedding) != self.embedding_dimensions:
            return memories
        semantic = await self.service.semantic_retrieve(
            identity,
            thread_id,
            embedding,
            self.similarity_threshold,
            self.limit,
        )
        return (
            semantic
            if (semantic.global_memories or semantic.thread_memories)
            else memories
        )
