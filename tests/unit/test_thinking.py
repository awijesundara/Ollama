from src.ui.thinking import format_thinking_text, thinking_display_seconds


def test_thinking_is_formatted_as_separate_readable_lines() -> None:
    formatted = format_thinking_text(
        "First inspect the request. Then choose the safest approach.\nVerify it."
    )
    assert formatted == (
        "**Thinking**\n\n"
        "- First inspect the request.\n"
        "- Then choose the safest approach.\n"
        "- Verify it."
    )


def test_incomplete_thought_is_held_until_its_line_is_ready() -> None:
    formatted = format_thinking_text(
        "First complete thought. Still arriving", include_incomplete=False
    )
    assert formatted == "**Thinking**\n\n- First complete thought."


def test_short_thinking_has_a_readable_minimum() -> None:
    assert thinking_display_seconds("Check the request and answer.") == 8.0


def test_longer_thinking_gets_more_reading_time() -> None:
    text = " ".join(["reasoning"] * 60)
    assert thinking_display_seconds(text) == 17


def test_very_long_thinking_does_not_linger_forever() -> None:
    text = " ".join(["reasoning"] * 1_000)
    assert thinking_display_seconds(text) == 30.0
