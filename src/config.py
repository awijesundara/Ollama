import base64
import binascii
from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, SecretStr, field_validator, model_validator
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
    STORAGE_BACKEND: Literal["encrypted_files", "postgresql"] = "encrypted_files"
    ENCRYPTED_STORAGE_DIR: str = "/var/lib/chainlit-ollama-memory/users"
    ENCRYPTED_STORAGE_KEY: SecretStr | None = None
    CHAINLIT_AUTH_SECRET: SecretStr | None = None
    CHAINLIT_URL: AnyHttpUrl = AnyHttpUrl("http://localhost:8000")
    AUTH_MODE: Literal["ldap", "header"] = "ldap"
    TRUSTED_IDENTITY_HEADER: str = "X-Remote-User-ID"
    TRUSTED_UPN_HEADER: str = "X-Remote-User"
    TRUSTED_DISPLAY_NAME_HEADER: str = "X-Remote-Display-Name"
    DATABASE_URL: str = "postgresql://chainlit:change-me@localhost/chainlit"
    DATABASE_POOL_MIN_SIZE: int = Field(2, ge=1)
    DATABASE_POOL_MAX_SIZE: int = Field(20, ge=1)
    OLLAMA_HOST: AnyHttpUrl = AnyHttpUrl("http://localhost:11434")
    OLLAMA_CHAT_MODEL: str = "gpt-oss:20b"
    OLLAMA_VISION_MODEL: str | None = None
    OLLAMA_EMBEDDING_MODEL: str = "embeddinggemma"
    OLLAMA_CONTEXT_LENGTH: int = Field(16384, ge=2048)
    OLLAMA_REQUEST_TIMEOUT: float = Field(300, gt=0)
    SHOW_MODEL_THINKING: bool = True
    ATTACHMENTS_ENABLED: bool = True
    ATTACHMENT_MAX_FILE_MB: int = Field(10, ge=1, le=100)
    ATTACHMENT_MAX_FILES: int = Field(10, ge=1, le=20)
    ATTACHMENT_MAX_EXTRACTED_CHARS: int = Field(100_000, ge=1_000, le=1_000_000)
    MEMORY_ENABLED: bool = True
    MEMORY_AUTO_EXTRACTION: bool = True
    MEMORY_MAX_GLOBAL_RESULTS: int = Field(10, ge=0, le=100)
    MEMORY_MAX_THREAD_RESULTS: int = Field(10, ge=0, le=100)
    MEMORY_MAX_ITEM_LENGTH: int = Field(500, ge=1, le=10_000)
    MEMORY_MAX_ITEMS_PER_USER: int = Field(500, ge=1)
    MEMORY_MIN_IMPORTANCE: int = Field(4, ge=1, le=10)
    MEMORY_VECTOR_SEARCH: bool = False
    MEMORY_SIMILARITY_THRESHOLD: float = Field(0.60, ge=0, le=1)
    MEMORY_EMBEDDING_DIMENSIONS: int = Field(768, ge=1)
    MEMORY_RETENTION_DAYS: int = Field(365, ge=1)
    AUDIT_RETENTION_DAYS: int = Field(365, ge=1)
    THREAD_RETENTION_DAYS: int = Field(730, ge=1)
    THREAD_RECENT_MESSAGE_LIMIT: int = Field(20, ge=1)
    THREAD_SUMMARY_ENABLED: bool = True
    THREAD_SUMMARY_TRIGGER_MESSAGES: int = Field(30, ge=2)
    LDAP_URI: str | None = None
    LDAP_BASE_DN: str | None = None
    LDAP_BIND_DN: str | None = None
    LDAP_BIND_PASSWORD: SecretStr | None = None
    LDAP_USER_FILTER: str | None = None
    LDAP_CA_FILE: str | None = None
    LDAP_CONNECT_TIMEOUT: float = Field(10, gt=0)
    LDAP_AUTH_RATE_LIMIT: int = Field(5, ge=1)
    LDAP_AUTH_RATE_WINDOW_SECONDS: int = Field(60, ge=1)
    LOG_USER_HASH_SALT: SecretStr | None = None

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        if not value.startswith(("postgresql://", "postgresql+asyncpg://")):
            raise ValueError("DATABASE_URL must be a PostgreSQL URL")
        return value.replace("postgresql+asyncpg://", "postgresql://", 1)

    @model_validator(mode="after")
    def validate_production(self) -> "Settings":
        if self.STORAGE_BACKEND == "encrypted_files":
            if self.ENCRYPTED_STORAGE_KEY is None and self.APP_ENV == "production":
                raise ValueError(
                    "ENCRYPTED_STORAGE_KEY is required for encrypted file storage"
                )
            if self.ENCRYPTED_STORAGE_KEY is not None:
                try:
                    decoded_key = base64.b64decode(
                        self.ENCRYPTED_STORAGE_KEY.get_secret_value(), validate=True
                    )
                except (binascii.Error, ValueError) as error:
                    raise ValueError(
                        "ENCRYPTED_STORAGE_KEY must be valid base64"
                    ) from error
                if len(decoded_key) != 32:
                    raise ValueError(
                        "ENCRYPTED_STORAGE_KEY must decode to exactly 32 bytes"
                    )
        if self.APP_ENV != "production":
            return self
        missing = [
            name
            for name, value in {
                "CHAINLIT_AUTH_SECRET": self.CHAINLIT_AUTH_SECRET,
                "LOG_USER_HASH_SALT": self.LOG_USER_HASH_SALT,
            }.items()
            if not value
        ]
        if self.AUTH_MODE == "ldap":
            missing.extend(
                name
                for name, value in {
                    "LDAP_URI": self.LDAP_URI,
                    "LDAP_BASE_DN": self.LDAP_BASE_DN,
                    "LDAP_CA_FILE": self.LDAP_CA_FILE,
                }.items()
                if not value
            )
        if missing:
            raise ValueError(
                "Missing required production settings: " + ", ".join(missing)
            )
        if self.AUTH_MODE == "ldap" and (
            not self.LDAP_URI or not self.LDAP_URI.lower().startswith("ldaps://")
        ):
            raise ValueError("LDAP_URI must use ldaps:// in production")
        if not str(self.CHAINLIT_URL).lower().startswith("https://"):
            raise ValueError("CHAINLIT_URL must use HTTPS in production")
        if self.DATABASE_POOL_MIN_SIZE > self.DATABASE_POOL_MAX_SIZE:
            raise ValueError("DATABASE_POOL_MIN_SIZE cannot exceed maximum")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Read and validate the environment once per process."""
    # BaseSettings fields are populated from the environment at runtime.
    return Settings()  # type: ignore[call-arg]
