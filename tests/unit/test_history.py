from src.chat.history import rebuild_history


def test_rebuild_history_skips_malformed_steps_and_limits_messages() -> None:
    steps = [
        {"type": "user_message", "input": "old"},
        {"type": "tool", "input": "hidden"},
        {"type": "user_message", "input": None},
        {"type": "assistant_message", "output": "answer"},
        {"type": "user_message", "input": "new"},
    ]
    messages = rebuild_history(steps, recent_limit=2)
    assert [(item.role, item.content) for item in messages] == [
        ("assistant", "answer"),
        ("user", "new"),
    ]
