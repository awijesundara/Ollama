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


def get_authenticated_identity() -> AuthenticatedIdentity:
    """Resolve identity exclusively from Chainlit's authenticated server session."""
    import chainlit as cl

    user = cl.user_session.get("user")
    if user is None:
        raise AuthenticationError("Authenticated user is unavailable")
    return identity_from_server_user(user.identifier, user.metadata)


def _optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) else None
