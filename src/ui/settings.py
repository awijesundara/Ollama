from typing import Any

import chainlit as cl
from chainlit.input_widget import Switch

from src.memory.models import MemoryPreferences


async def send_memory_settings(preferences: MemoryPreferences) -> None:
    inputs: list[Any] = [
        Switch(
            id="memory_enabled",
            label="Use saved memory",
            initial=preferences.memory_enabled,
        ),
        Switch(
            id="automatic_memory_enabled",
            label="Automatically save durable facts",
            initial=preferences.automatic_memory_enabled,
        ),
        Switch(
            id="allow_global_memory",
            label="Allow global memory",
            initial=preferences.allow_global_memory,
        ),
        Switch(
            id="allow_thread_memory",
            label="Allow chat memory",
            initial=preferences.allow_thread_memory,
        ),
    ]
    await cl.ChatSettings(inputs).send()


def memory_actions() -> list[cl.Action]:
    return [
        cl.Action(name="view_memories", label="View my memories", payload={}),
        cl.Action(name="add_global", label="Add global memory", payload={}),
        cl.Action(name="add_thread", label="Add chat memory", payload={}),
        cl.Action(name="delete_memory", label="Delete memory", payload={}),
        cl.Action(name="export_memories", label="Export my data", payload={}),
        cl.Action(name="storage_location", label="Where is my data?", payload={}),
        cl.Action(name="clear_global", label="Clear global", payload={}),
        cl.Action(name="clear_thread", label="Clear this chat", payload={}),
        cl.Action(name="disable_memory", label="Disable memory", payload={}),
    ]
