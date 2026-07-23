import json
import time
from collections.abc import AsyncIterator
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from src.monitoring import OLLAMA_DURATION, OLLAMA_REQUESTS
from src.ollama.models import (
    ChatMessage,
    OllamaModelNotFoundError,
    OllamaResponseError,
    OllamaUnavailableError,
)

ResponseModel = TypeVar("ResponseModel", bound=BaseModel)


class OllamaService:
    def __init__(
        self,
        host: str,
        chat_model: str,
        embedding_model: str,
        timeout: float,
    ) -> None:
        self._chat_model = chat_model
        self._embedding_model = embedding_model
        self._client = httpx.AsyncClient(
            base_url=host.rstrip("/"),
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def stream_chat(
        self, messages: list[ChatMessage]
    ) -> AsyncIterator[str]:
        payload = {
            "model": self._chat_model,
            "messages": [message.model_dump() for message in messages],
            "stream": True,
        }
        started = time.monotonic()
        status = "success"
        try:
            async with self._client.stream("POST", "/api/chat", json=payload) as response:
                await self._raise_for_status(response)
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                        content = chunk.get("message", {}).get("content", "")
                    except (json.JSONDecodeError, AttributeError) as error:
                        raise OllamaResponseError(
                            "Malformed streaming response"
                        ) from error
                    if content:
                        yield str(content)
        except httpx.RequestError as error:
            status = "error"
            raise OllamaUnavailableError("Ollama is unavailable") from error
        except RuntimeError:
            status = "error"
            raise
        finally:
            OLLAMA_REQUESTS.labels(operation="chat_stream", status=status).inc()
            OLLAMA_DURATION.labels(operation="chat_stream").observe(
                time.monotonic() - started
            )

    async def structured_chat(
        self,
        messages: list[ChatMessage],
        response_schema: type[ResponseModel],
    ) -> ResponseModel:
        payload = {
            "model": self._chat_model,
            "messages": [message.model_dump() for message in messages],
            "format": response_schema.model_json_schema(),
            "options": {"temperature": 0},
            "stream": False,
        }
        result = await self._post("/api/chat", payload)
        try:
            content = result["message"]["content"]
            return response_schema.model_validate_json(content)
        except (KeyError, TypeError, ValidationError) as error:
            raise OllamaResponseError("Invalid structured response") from error

    async def create_embedding(self, text: str) -> list[float]:
        result = await self._post(
            "/api/embed", {"model": self._embedding_model, "input": text}
        )
        try:
            embedding = result["embeddings"][0]
            return [float(item) for item in embedding]
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise OllamaResponseError("Invalid embedding response") from error

    async def health_check(self) -> bool:
        try:
            response = await self._client.get("/api/tags")
            return response.status_code == 200
        except httpx.RequestError:
            return False

    async def models_available(self, required: set[str]) -> bool:
        try:
            result = await self._post("/api/tags", None, method="GET")
            names = {str(model.get("name", "")) for model in result.get("models", [])}
            return all(
                wanted in names or any(name.startswith(f"{wanted}:") for name in names)
                for wanted in required
            )
        except OllamaUnavailableError:
            return False

    async def _post(
        self,
        path: str,
        payload: dict[str, Any] | None,
        *,
        method: str = "POST",
    ) -> dict[str, Any]:
        started = time.monotonic()
        status = "success"
        operation = path.removeprefix("/api/")
        try:
            response = await self._client.request(method, path, json=payload)
            await self._raise_for_status(response)
            return dict(response.json())
        except httpx.RequestError as error:
            status = "error"
            raise OllamaUnavailableError("Ollama is unavailable") from error
        except (json.JSONDecodeError, TypeError) as error:
            status = "error"
            raise OllamaResponseError("Malformed Ollama response") from error
        except RuntimeError:
            status = "error"
            raise
        finally:
            OLLAMA_REQUESTS.labels(operation=operation, status=status).inc()
            OLLAMA_DURATION.labels(operation=operation).observe(
                time.monotonic() - started
            )

    async def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code == 404:
            raise OllamaModelNotFoundError("Required Ollama model was not found")
        if response.is_error:
            raise OllamaUnavailableError("Ollama request failed")
