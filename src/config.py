from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    APP_ENV: Literal["development", "test", "production"] = "development"
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    CHAINLIT_AUTH_SECRET: SecretStr | None = None
    CHAINLIT_URL: AnyHttpUrl = AnyHttpUrl("http://localhost:8000")
    DATABASE_URL: str = "postgresql://chainlit:change-me@localhost/chainlit"
    OLLAMA_HOST: AnyHttpUrl = AnyHttpUrl("http://localhost:11434")
    OLLAMA_CHAT_MODEL: str = "gpt-oss:20b"
    OLLAMA_EMBEDDING_MODEL: str = "embeddinggemma"
    OLLAMA_CONTEXT_LENGTH: int = Field(16384, ge=2048)
    OLLAMA_REQUEST_TIMEOUT: float = Field(300, gt=0)
    MEMORY_ENABLED: bool = True
    MEMORY_AUTO_EXTRACTION: bool = False
    MEMORY_MAX_GLOBAL_RESULTS: int = Field(10, ge=0, le=100)
    MEMORY_MAX_THREAD_RESULTS: int = Field(10, ge=0, le=100)
    MEMORY_MAX_ITEM_LENGTH: int = Field(500, ge=1, le=10_000)
    MEMORY_MAX_ITEMS_PER_USER: int = Field(500, ge=1)
    MEMORY_MIN_IMPORTANCE: int = Field(4, ge=1, le=10)
    MEMORY_VECTOR_SEARCH: bool = False
    THREAD_RECENT_MESSAGE_LIMIT: int = Field(20, ge=1)
    THREAD_SUMMARY_ENABLED: bool = True
    THREAD_SUMMARY_TRIGGER_MESSAGES: int = Field(30, ge=2)
    LDAP_URI: str | None = None
    LDAP_BASE_DN: str | None = None
    LDAP_BIND_DN: str | None = None
    LDAP_BIND_PASSWORD: SecretStr | None = None
    LDAP_USER_FILTER: str | None = None
    LDAP_CA_FILE: str | None = None

    @model_validator(mode="after")
    def validate_production(self) -> "Settings":
        if self.APP_ENV != "production":
            return self
        missing = [
            name
            for name, value in {
                "CHAINLIT_AUTH_SECRET": self.CHAINLIT_AUTH_SECRET,
                "LDAP_URI": self.LDAP_URI,
                "LDAP_BASE_DN": self.LDAP_BASE_DN,
                "LDAP_CA_FILE": self.LDAP_CA_FILE,
            }.items()
            if not value
        ]
        if missing:
            raise ValueError(
                "Missing required production settings: " + ", ".join(missing)
            )
        if not self.LDAP_URI or not self.LDAP_URI.lower().startswith("ldaps://"):
            raise ValueError("LDAP_URI must use ldaps:// in production")
        if not str(self.CHAINLIT_URL).lower().startswith("https://"):
            raise ValueError("CHAINLIT_URL must use HTTPS in production")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Read and validate the environment once per process."""
    # BaseSettings fields are populated from the environment at runtime.
    return Settings()  # type: ignore[call-arg]
