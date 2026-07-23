import hashlib
import re
import unicodedata
from dataclasses import dataclass

from src.memory.models import MemoryCreate, MemorySource
from src.security.secret_detection import detect_secret


class MemoryValidationError(ValueError):
    def __init__(self, reason: str) -> None:
        super().__init__("Memory was rejected")
        self.reason = reason


@dataclass(frozen=True, slots=True)
class ValidatedMemory:
    display_text: str
    normalized_text: str
    normalized_hash: str


_INJECTION = re.compile(
    r"(ignore (?:all |any )?(?:previous|prior) instructions|"
    r"act as (?:the )?system|reveal all memor(?:y|ies)|"
    r"use another user(?:'s)? profile|execute this sql)",
    re.I,
)
_TEMPORARY = re.compile(
    r"\b(?:just for today|only today|temporary incident|one[- ]time issue)\b",
    re.I,
)
_LOG_LINE = re.compile(
    r"(?m)^(?:\d{4}-\d{2}-\d{2}[T ]|\[[A-Z]+\]|[A-Z]+:\s)"
)
_SENSITIVE_AUTOMATIC = re.compile(
    r"\b(?:medical|diagnosis|health condition|salary|performance review|"
    r"human resources|hr complaint|legal dispute|disciplinary)\b",
    re.I,
)


class MemoryValidator:
    def __init__(self, max_length: int) -> None:
        self.max_length = max_length

    def validate(self, request: MemoryCreate) -> ValidatedMemory:
        if request.text.count("\n") > 20 or len(_LOG_LINE.findall(request.text)) > 10:
            raise MemoryValidationError("raw_log_or_document")
        display = collapse_whitespace(request.text)
        if not display:
            raise MemoryValidationError("empty")
        if len(display) > self.max_length:
            raise MemoryValidationError("too_long")
        secret = detect_secret(display)
        if secret:
            raise MemoryValidationError(f"secret:{secret.kind}")
        if _INJECTION.search(display):
            raise MemoryValidationError("prompt_injection")
        if request.source is MemorySource.AUTOMATIC and _TEMPORARY.search(display):
            raise MemoryValidationError("temporary")
        if request.source is MemorySource.AUTOMATIC and (
            _SENSITIVE_AUTOMATIC.search(display)
            or request.category.casefold()
            in {"medical", "health", "hr", "salary", "legal", "financial"}
        ):
            raise MemoryValidationError("sensitive_category")
        normalized = unicodedata.normalize("NFKC", display).casefold()
        return ValidatedMemory(
            display_text=display,
            normalized_text=normalized,
            normalized_hash=hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
        )


def collapse_whitespace(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).split())
