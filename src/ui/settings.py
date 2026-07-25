from typing import Any

import chainlit as cl
from chainlit.input_widget import Select, Slider, Switch, TextInput

from src.memory.models import MemoryPreferences

PERSONALITY_OPTIONS = [
    "Default · Clear and neutral",
    "Professional · Polished and precise",
    "Friendly · Warm and conversational",
    "Candid · Direct and constructive",
    "Quirky · Playful and imaginative",
    "Efficient · Concise and practical",
]


def default_chat_preferences(preferences: MemoryPreferences) -> dict[str, Any]:
    return {
        "personality": PERSONALITY_OPTIONS[0],
        "response_detail": "Balanced",
        "response_language": "Automatic",
        "custom_instructions": "",
        "temperature": 0.7,
        "show_thinking": True,
        "attachments_enabled": True,
        "image_analysis_enabled": True,
        "thread_summaries_enabled": True,
        "memory_enabled": preferences.memory_enabled,
        "automatic_memory_enabled": preferences.automatic_memory_enabled,
        "allow_global_memory": preferences.allow_global_memory,
        "allow_thread_memory": preferences.allow_thread_memory,
    }


async def send_memory_settings(
    preferences: MemoryPreferences,
    current: dict[str, Any] | None = None,
) -> None:
    values = default_chat_preferences(preferences) | (current or {})
    inputs: list[Any] = [
        Select(
            id="personality",
            label="Personalization · Base style and tone",
            values=PERSONALITY_OPTIONS,
            initial=str(values["personality"]),
            description="Changes how responses feel, without changing capabilities.",
        ),
        Select(
            id="response_detail",
            label="Personalization · Response detail",
            values=["Concise", "Balanced", "Detailed"],
            initial=str(values["response_detail"]),
            description="Controls the default amount of explanation.",
        ),
        Select(
            id="response_language",
            label="Personalization · Response language",
            values=["Automatic", "English", "Japanese", "Sinhala"],
            initial=str(values["response_language"]),
            description="Automatic follows the language of your message.",
        ),
        TextInput(
            id="custom_instructions",
            label="Personalization · Custom instructions",
            initial=str(values["custom_instructions"]),
            placeholder="How should the assistant respond? What should it know?",
            multiline=True,
            description="Applied to future responses in this session.",
        ),
        Slider(
            id="temperature",
            label="Model · Creativity",
            initial=float(values["temperature"]),
            min=0,
            max=1.5,
            step=0.1,
            description="Lower is more consistent; higher is more varied.",
        ),
        Switch(
            id="show_thinking",
            label="Model · Show reasoning activity",
            initial=bool(values["show_thinking"]),
            description="Shows one transient reasoning line at a time.",
        ),
        Switch(
            id="attachments_enabled",
            label="Capabilities · Process documents",
            initial=bool(values["attachments_enabled"]),
            description="Allow PDF, DOCX, text, code, and structured files.",
        ),
        Switch(
            id="image_analysis_enabled",
            label="Capabilities · Analyze images",
            initial=bool(values["image_analysis_enabled"]),
            description="Use the configured local vision model for images.",
        ),
        Switch(
            id="thread_summaries_enabled",
            label="Conversations · Summarize long chats",
            initial=bool(values["thread_summaries_enabled"]),
            description="Maintains useful context when conversations become long.",
        ),
        Switch(
            id="memory_enabled",
            label="Personalization · Use saved memory",
            initial=bool(values["memory_enabled"]),
            description="Use relevant encrypted memories in responses.",
        ),
        Switch(
            id="automatic_memory_enabled",
            label="Personalization · Learn useful preferences",
            initial=bool(values["automatic_memory_enabled"]),
            description="Automatically save durable facts and preferences.",
        ),
        Switch(
            id="allow_global_memory",
            label="Memory · Use across conversations",
            initial=bool(values["allow_global_memory"]),
            description="Make selected memories available in future chats.",
        ),
        Switch(
            id="allow_thread_memory",
            label="Memory · Use within this conversation",
            initial=bool(values["allow_thread_memory"]),
            description="Keep memories scoped to the current chat.",
        ),
    ]
    await cl.ChatSettings(inputs).send()
