import pytest

from src.memory.commands import CommandKind, parse_memory_command
from src.memory.models import MemoryScope


def test_remember_defaults_to_global() -> None:
    command = parse_memory_command("/remember I prefer concise answers")
    assert command is not None
    assert command.kind is CommandKind.REMEMBER
    assert command.scope is MemoryScope.GLOBAL
    assert command.argument == "I prefer concise answers"


def test_thread_memory_command() -> None:
    command = parse_memory_command("/remember-chat This uses PostgreSQL 16")
    assert command is not None
    assert command.scope is MemoryScope.THREAD


def test_non_command_is_not_consumed() -> None:
    assert parse_memory_command("Explain /remember") is None
    assert parse_memory_command("/unknown thing") is None


def test_missing_argument_is_clear() -> None:
    with pytest.raises(ValueError, match="requires an argument"):
        parse_memory_command("/forget")
