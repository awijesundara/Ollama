import math
import re

MIN_THINKING_DISPLAY_SECONDS = 8.0
MAX_THINKING_DISPLAY_SECONDS = 30.0
READING_WORDS_PER_MINUTE = 220


def thinking_lines(text: str, *, include_incomplete: bool = True) -> list[str]:
    """Split reasoning at sentence and explicit line boundaries."""
    normalized = re.sub(r"[ \t]+", " ", text.strip())
    fragments = re.split(r"(?:\r?\n)+|(?<=[.!?。！？])\s+", normalized)
    lines = [fragment.strip() for fragment in fragments if fragment.strip()]
    if (
        not include_incomplete
        and lines
        and not re.search(r"[.!?。！？]\s*$", normalized)
        and not text.endswith(("\n", "\r"))
    ):
        lines.pop()
    return lines


def format_thinking_text(
    text: str, *, include_incomplete: bool = True
) -> str:
    """Present model reasoning as short, individually readable thought lines."""
    lines = thinking_lines(text, include_incomplete=include_incomplete)
    if not lines:
        return "**Thinking**\n\nWorking through this…"
    return "**Thinking**\n\n" + "\n".join(f"- {line}" for line in lines)


def thinking_display_seconds(text: str) -> float:
    """Return a comfortable, bounded reading window for transient reasoning."""
    words = re.findall(r"\S+", text)
    reading_seconds = len(words) * 60 / READING_WORDS_PER_MINUTE
    punctuation_pauses = len(re.findall(r"[.!?。！？]", text)) * 0.18
    return min(
        MAX_THINKING_DISPLAY_SECONDS,
        max(
            MIN_THINKING_DISPLAY_SECONDS,
            math.ceil(reading_seconds + punctuation_pauses),
        ),
    )
