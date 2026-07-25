from src.ui.thinking import format_activity_text


def test_activity_is_formatted_as_a_single_ghost_status() -> None:
    assert (
        format_activity_text("  Reading   uploaded files... ")
        == "**Reading uploaded files…**"
    )


def test_activity_does_not_expose_reasoning_markup() -> None:
    assert "\n" not in format_activity_text("Preparing response")
