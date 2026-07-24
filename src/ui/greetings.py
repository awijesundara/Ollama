import secrets

GREETINGS = (
    "What are we working on?",
    "Bring me an idea, a question, or a challenge.",
    "Where should we begin?",
    "What can we make clearer today?",
    "Ready when you are—what’s on your mind?",
    "Let’s build something useful.",
    "What would you like to figure out?",
    "Start anywhere. We’ll shape it together.",
    "What deserves a closer look?",
    "Share the problem. I’ll help untangle it.",
    "What shall we explore?",
    "Drop in a thought, file, or question.",
)

_last_greeting: str | None = None


def choose_greeting(previous: str | None = None) -> str:
    """Choose a generic greeting without immediately repeating the last one."""
    global _last_greeting
    excluded = previous or _last_greeting
    choices = [greeting for greeting in GREETINGS if greeting != excluded]
    selected = secrets.choice(choices or list(GREETINGS))
    _last_greeting = selected
    return selected
