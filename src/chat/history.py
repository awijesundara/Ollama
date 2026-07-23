from typing import Any

from src.ollama.models import ChatMessage


def rebuild_history(
    steps: list[dict[str, Any]], recent_limit: int | None = None
) -> list[ChatMessage]:
    messages: list[ChatMessage] = []
    for step in steps:
        step_type = step.get("type")
        if step_type == "assistant_message":
            raw = step.get("output") or step.get("input")
        else:
            raw = step.get("input") or step.get("output")
        if not isinstance(raw, str) or not raw.strip():
            continue
        if step_type == "user_message":
            messages.append(ChatMessage(role="user", content=raw))
        elif step_type == "assistant_message":
            messages.append(ChatMessage(role="assistant", content=raw))
    return messages[-recent_limit:] if recent_limit else messages
