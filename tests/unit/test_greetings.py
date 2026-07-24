from src.ui.greetings import GREETINGS, choose_greeting


def test_greeting_is_generic_and_from_the_curated_set() -> None:
    assert choose_greeting() in GREETINGS


def test_greeting_does_not_immediately_repeat() -> None:
    for previous in GREETINGS:
        assert choose_greeting(previous) != previous
