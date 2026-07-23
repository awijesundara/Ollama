import pytest

from src.auth.identity import AuthenticationError, identity_from_server_user


def test_uses_server_identifier_not_metadata() -> None:
    identity = identity_from_server_user(
        "immutable-guid",
        {"user_identifier": "forged", "display_name": "Alice"},
    )
    assert identity.user_identifier == "immutable-guid"
    assert identity.display_name == "Alice"


@pytest.mark.parametrize("identifier", [None, "", "  "])
def test_rejects_missing_identity(identifier: str | None) -> None:
    with pytest.raises(AuthenticationError):
        identity_from_server_user(identifier)
