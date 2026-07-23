from src.auth.identity import AuthenticatedIdentity
from src.memory.models import ConflictAssessment, MemoryCreate
from src.memory.service import MemoryService
from src.ollama.client import OllamaService
from src.ollama.models import ChatMessage


class ConflictDetector:
    def __init__(self, memory: MemoryService, ollama: OllamaService) -> None:
        self._memory = memory
        self._ollama = ollama

    async def find(
        self,
        identity: AuthenticatedIdentity,
        request: MemoryCreate,
    ) -> ConflictAssessment:
        existing = await self._memory.list_memories(
            identity,
            scope=request.scope,
            thread_id=request.thread_id,
        )
        if not existing:
            return ConflictAssessment(conflicts=False)
        catalog = "\n".join(f"{item.id}: {item.text}" for item in existing[:100])
        prompt = (
            "Determine whether the proposed memory directly contradicts exactly "
            "one existing memory. Related or additive facts are not conflicts. "
            "Only return an ID from the catalog.\n\n"
            f"Existing:\n{catalog}\n\nProposed:\n{request.text}"
        )
        try:
            result = await self._ollama.structured_chat(
                [ChatMessage(role="user", content=prompt)],
                ConflictAssessment,
            )
        except RuntimeError:
            return ConflictAssessment(conflicts=False)
        valid_ids = {item.id for item in existing}
        if result.conflicting_memory_id not in valid_ids:
            return ConflictAssessment(conflicts=False)
        return result
