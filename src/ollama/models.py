from typing import Literal

from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class OllamaUnavailableError(RuntimeError):
    pass


class OllamaModelNotFoundError(RuntimeError):
    pass


class OllamaResponseError(RuntimeError):
    pass
