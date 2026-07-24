import asyncio

from src.chat.file_summaries import EncryptedFileThreadSummaryRepository
from src.chat.summarizer import (
    SummaryRepository,
    ThreadSummarizer,
    ThreadSummaryRepository,
)
from src.config import Settings, get_settings
from src.database.chainlit_layer import create_chainlit_data_layer
from src.database.connection import Database
from src.database.encrypted_file_layer import EncryptedFileDataLayer
from src.memory.conflicts import ConflictDetector
from src.memory.extractor import MemoryExtractor
from src.memory.file_repository import EncryptedFileMemoryRepository
from src.memory.repository import MemoryRepository, PostgresMemoryRepository
from src.memory.retriever import MemoryRetriever
from src.memory.service import MemoryService
from src.memory.validator import MemoryValidator
from src.ollama.client import OllamaService
from src.security.audit import AuditRepository, AuditWriter
from src.security.file_audit import EncryptedFileAuditRepository
from src.storage.encrypted_store import EncryptedUserStore


class ApplicationServices:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.database = Database(
            settings.DATABASE_URL,
            settings.DATABASE_POOL_MIN_SIZE,
            settings.DATABASE_POOL_MAX_SIZE,
        )
        self.file_store: EncryptedUserStore | None = None
        if settings.STORAGE_BACKEND == "encrypted_files":
            if settings.ENCRYPTED_STORAGE_KEY is None:
                raise RuntimeError(
                    "ENCRYPTED_STORAGE_KEY is required for encrypted file storage"
                )
            self.file_store = EncryptedUserStore(
                settings.ENCRYPTED_STORAGE_DIR,
                settings.ENCRYPTED_STORAGE_KEY.get_secret_value(),
            )
            self.data_layer = EncryptedFileDataLayer(self.file_store)
        else:
            self.data_layer = create_chainlit_data_layer(settings.DATABASE_URL)
        self.ollama = OllamaService(
            str(settings.OLLAMA_HOST),
            settings.OLLAMA_CHAT_MODEL,
            settings.OLLAMA_EMBEDDING_MODEL,
            settings.OLLAMA_REQUEST_TIMEOUT,
        )
        self.memory: MemoryService | None = None
        self.retriever: MemoryRetriever | None = None
        self.extractor: MemoryExtractor | None = None
        self.conflicts: ConflictDetector | None = None
        self.summaries: SummaryRepository | None = None
        self.summarizer: ThreadSummarizer | None = None
        self.audit: AuditWriter | None = None
        self._start_lock = asyncio.Lock()

    async def start(self) -> None:
        if self.memory is not None:
            return
        async with self._start_lock:
            if self.memory is not None:
                return
            repository: MemoryRepository
            if self.file_store is not None:
                await self.file_store.initialize()
                repository = EncryptedFileMemoryRepository(self.file_store)
                self.audit = EncryptedFileAuditRepository(self.file_store)
                self.summaries = EncryptedFileThreadSummaryRepository(self.file_store)
            else:
                await self.database.start()
                repository = PostgresMemoryRepository(self.database.pool)
                self.audit = AuditRepository(self.database.pool)
                self.summaries = ThreadSummaryRepository(self.database.pool)
            self.memory = MemoryService(
                repository,
                MemoryValidator(self.settings.MEMORY_MAX_ITEM_LENGTH),
                max_items_per_user=self.settings.MEMORY_MAX_ITEMS_PER_USER,
                max_global_results=self.settings.MEMORY_MAX_GLOBAL_RESULTS,
                max_thread_results=self.settings.MEMORY_MAX_THREAD_RESULTS,
            )
            self.retriever = MemoryRetriever(
                self.memory,
                self.ollama,
                semantic_enabled=self.settings.MEMORY_VECTOR_SEARCH,
                similarity_threshold=self.settings.MEMORY_SIMILARITY_THRESHOLD,
                limit=(
                    self.settings.MEMORY_MAX_GLOBAL_RESULTS
                    + self.settings.MEMORY_MAX_THREAD_RESULTS
                ),
                embedding_dimensions=self.settings.MEMORY_EMBEDDING_DIMENSIONS,
            )
            self.conflicts = ConflictDetector(self.memory, self.ollama)
            self.extractor = MemoryExtractor(
                self.ollama,
                self.memory,
                self.settings.MEMORY_MIN_IMPORTANCE,
                conflict_detector=self.conflicts,
                retention_days=self.settings.MEMORY_RETENTION_DAYS,
                create_embeddings=self.settings.MEMORY_VECTOR_SEARCH,
                audit=self.audit,
                embedding_dimensions=self.settings.MEMORY_EMBEDDING_DIMENSIONS,
            )
            self.summarizer = ThreadSummarizer(
                self.summaries,
                self.ollama,
                self.settings.THREAD_SUMMARY_TRIGGER_MESSAGES,
                self.settings.THREAD_RECENT_MESSAGE_LIMIT,
            )

    async def storage_health_check(self) -> bool:
        if self.file_store is not None:
            return await self.file_store.health_check()
        return await self.database.health_check()

    def user_storage_location(self, user_identifier: str) -> str:
        if self.file_store is not None:
            return self.file_store.public_location(user_identifier)
        return "PostgreSQL (server-managed)"

    def require_memory(self) -> MemoryService:
        if self.memory is None:
            raise RuntimeError("Application services have not started")
        return self.memory

    def require_retriever(self) -> MemoryRetriever:
        if self.retriever is None:
            raise RuntimeError("Application services have not started")
        return self.retriever


services = ApplicationServices(get_settings())
