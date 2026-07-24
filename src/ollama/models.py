from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str
    images: list[str] | None = None


@dataclass(frozen=True, slots=True)
class ChatStreamChunk:
    content: str = ""
    thinking: str = ""


class OllamaUnavailableError(RuntimeError):
    pass


class OllamaModelNotFoundError(RuntimeError):
    pass


class OllamaResponseError(RuntimeError):
    pass
