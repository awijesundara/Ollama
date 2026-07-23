from prometheus_client import Counter, Gauge, Histogram

ACTIVE_SESSIONS = Gauge(
    "chainlit_active_sessions", "Current authenticated Chainlit sessions"
)
OLLAMA_REQUESTS = Counter(
    "ollama_requests_total", "Ollama requests", ["operation", "status"]
)
OLLAMA_DURATION = Histogram(
    "ollama_request_duration_seconds", "Ollama request duration", ["operation"]
)
MEMORY_READS = Counter("memory_reads_total", "Memory retrieval operations")
MEMORY_CREATES = Counter("memory_creates_total", "Memories created", ["source"])
MEMORY_REJECTIONS = Counter("memory_rejections_total", "Rejected memories", ["reason"])
MEMORY_DELETES = Counter("memory_deletes_total", "Memories deleted", ["scope"])
MEMORY_RETRIEVAL_DURATION = Histogram(
    "memory_retrieval_duration_seconds", "Memory retrieval duration"
)
THREAD_RESUMES = Counter("thread_resumes_total", "Threads resumed")
THREAD_SUMMARY_UPDATES = Counter(
    "thread_summary_updates_total", "Thread summary updates"
)
DATABASE_POOL_USAGE = Gauge(
    "database_pool_usage", "Checked-out PostgreSQL pool connections"
)
