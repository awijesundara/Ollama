from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


class AuthenticationError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class AuthenticatedIdentity:
    user_identifier: str
    display_name: str | None = None
    upn: str | None = None

    def __post_init__(self) -> None:
        if not self.user_identifier.strip():
            raise AuthenticationError("Authenticated user identifier is empty")


def identity_from_server_user(
    identifier: str | None,
    metadata: Mapping[str, Any] | None = None,
) -> AuthenticatedIdentity:
    """Create identity from a trusted server-side auth result, never a payload."""
    if identifier is None or not identifier.strip():
        raise AuthenticationError("Authenticated user identifier is unavailable")
    metadata = metadata or {}
    return AuthenticatedIdentity(
        user_identifier=identifier.strip(),
        display_name=_optional_string(metadata.get("display_name")),
        upn=_optional_string(metadata.get("upn")),
    )


def trusted_header_value(
    value: str | None,
    *,
    required: bool = False,
    max_length: int = 512,
) -> str | None:
    """Validate a value supplied by the trusted authentication proxy."""
    normalized = value.strip() if isinstance(value, str) else ""
    if any(ord(character) < 32 or ord(character) == 127 for character in normalized):
        raise AuthenticationError("Trusted identity header contains control characters")
    if len(normalized) > max_length:
        raise AuthenticationError("Trusted identity header is too long")
    if required and not normalized:
        raise AuthenticationError("Trusted identity header is unavailable")
    return normalized or None


def identity_from_google_claims(
    claims: Mapping[str, Any],
    allowed_domain: str | None = None,
) -> AuthenticatedIdentity:
    """Build an identity from Google's verified OAuth user-info claims."""
    subject = _optional_string(claims.get("sub"))
    if subject is None or not subject.strip():
        raise AuthenticationError("Google account identifier is unavailable")
    if claims.get("email_verified") is not True:
        raise AuthenticationError("Google account email is not verified")
    hosted_domain = _optional_string(claims.get("hd"))
    if allowed_domain and (
        hosted_domain is None
        or hosted_domain.casefold() != allowed_domain.strip().casefold()
    ):
        raise AuthenticationError("Google account domain is not allowed")
    return AuthenticatedIdentity(
        user_identifier=f"google:{subject.strip()}",
        display_name=_optional_string(claims.get("name")),
        upn=_optional_string(claims.get("email")),
    )


def get_authenticated_identity() -> AuthenticatedIdentity:
    """Resolve identity exclusively from Chainlit's authenticated server session."""
    import chainlit as cl

    user = cl.user_session.get("user")
    if user is None:
        raise AuthenticationError("Authenticated user is unavailable")
    return identity_from_server_user(user.identifier, user.metadata)


def _optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) else None
