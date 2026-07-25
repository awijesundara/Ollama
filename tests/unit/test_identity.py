import pytest

from src.auth.identity import (
    AuthenticationError,
    identity_from_google_claims,
    identity_from_server_user,
    trusted_header_value,
)


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


def test_google_identity_uses_immutable_subject() -> None:
    identity = identity_from_google_claims(
        {
            "sub": "1234567890",
            "email": "alice@example.com",
            "email_verified": True,
            "name": "Alice",
            "hd": "example.com",
        },
        allowed_domain="EXAMPLE.COM",
    )
    assert identity.user_identifier == "google:1234567890"
    assert identity.upn == "alice@example.com"


@pytest.mark.parametrize(
    "claims",
    [
        {"email": "alice@example.com", "email_verified": True},
        {"sub": "123", "email": "alice@example.com", "email_verified": False},
        {
            "sub": "123",
            "email": "alice@other.example",
            "email_verified": True,
            "hd": "other.example",
        },
    ],
)
def test_google_identity_rejects_untrusted_claims(claims: dict[str, object]) -> None:
    with pytest.raises(AuthenticationError):
        identity_from_google_claims(claims, allowed_domain="example.com")


def test_trusted_header_value_normalizes_safe_text() -> None:
    assert trusted_header_value("  Alice Example  ") == "Alice Example"
    assert trusted_header_value("   ") is None


@pytest.mark.parametrize("value", ["alice\nadmin", "alice\x00admin", "x" * 513])
def test_trusted_header_value_rejects_unsafe_text(value: str) -> None:
    with pytest.raises(AuthenticationError):
        trusted_header_value(value)
