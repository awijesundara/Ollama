import shlex
from dataclasses import dataclass
from enum import StrEnum

from src.memory.models import MemoryScope


class CommandKind(StrEnum):
    REMEMBER = "remember"
    LIST = "list"
    FORGET = "forget"
    MEMORY_ON = "memory_on"
    MEMORY_OFF = "memory_off"
    AUTO_MEMORY_ON = "auto_memory_on"
    AUTO_MEMORY_OFF = "auto_memory_off"
    FORGET_ALL_GLOBAL = "forget_all_global"
    FORGET_ALL_THREAD = "forget_all_thread"


@dataclass(frozen=True, slots=True)
class MemoryCommand:
    kind: CommandKind
    argument: str | None = None
    scope: MemoryScope | None = None


_NO_ARGUMENT = {
    "/memories": CommandKind.LIST,
    "/memory-on": CommandKind.MEMORY_ON,
    "/memory-off": CommandKind.MEMORY_OFF,
    "/auto-memory-on": CommandKind.AUTO_MEMORY_ON,
    "/auto-memory-off": CommandKind.AUTO_MEMORY_OFF,
    "/forget-all-global": CommandKind.FORGET_ALL_GLOBAL,
    "/forget-all-chat": CommandKind.FORGET_ALL_THREAD,
}


def parse_memory_command(text: str) -> MemoryCommand | None:
    stripped = text.strip()
    if not stripped.startswith("/"):
        return None
    name, _, raw_argument = stripped.partition(" ")
    if name in _NO_ARGUMENT:
        if raw_argument.strip():
            raise ValueError(f"{name} does not accept an argument")
        return MemoryCommand(kind=_NO_ARGUMENT[name])
    if name in {"/remember", "/remember-global", "/remember-chat", "/forget"}:
        argument = raw_argument.strip()
        if not argument:
            raise ValueError(f"{name} requires an argument")
        # Reject malformed quoting but preserve ordinary user text.
        shlex.split(argument)
        if name == "/forget":
            return MemoryCommand(CommandKind.FORGET, argument=argument)
        scope = MemoryScope.THREAD if name == "/remember-chat" else MemoryScope.GLOBAL
        return MemoryCommand(CommandKind.REMEMBER, argument=argument, scope=scope)
    return None
