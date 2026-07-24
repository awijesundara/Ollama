import json

import httpx
import pytest

from src.ollama.client import OllamaService
from src.ollama.models import ChatMessage


@pytest.mark.asyncio
async def test_stream_chat_events_separates_thinking_from_answer() -> None:
    response_body = "\n".join(
        [
            json.dumps({"message": {"thinking": "considering"}}),
            json.dumps({"message": {"content": "answer"}}),
        ]
    )

    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=response_body)

    service = OllamaService("http://ollama", "chat", "embed", 10)
    await service._client.aclose()
    service._client = httpx.AsyncClient(
        base_url="http://ollama",
        transport=httpx.MockTransport(handler),
    )
    try:
        chunks = [
            chunk
            async for chunk in service.stream_chat_events(
                [ChatMessage(role="user", content="hello")]
            )
        ]
    finally:
        await service.close()

    assert chunks[0].thinking == "considering"
    assert chunks[0].content == ""
    assert chunks[1].content == "answer"
