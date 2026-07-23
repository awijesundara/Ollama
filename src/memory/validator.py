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


class MemoryValidator:
    def __init__(self, max_length: int) -> None:
        self.max_length = max_length

    def validate(self, request: MemoryCreate) -> ValidatedMemory:
        display = collapse_whitespace(request.text)
        if not display:
            raise MemoryValidationError("empty")
        if len(display) > self.max_length:
            raise MemoryValidationError("too_long")
        secret = detect_secret(display)
        if secret:
            raise MemoryValidationError(f"secret:{secret.kind}")
        if request.source is MemorySource.AUTOMATIC and _INJECTION.search(display):
            raise MemoryValidationError("prompt_injection")
        normalized = unicodedata.normalize("NFKC", display).casefold()
        return ValidatedMemory(
            display_text=display,
            normalized_text=normalized,
            normalized_hash=hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
        )


def collapse_whitespace(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).split())
