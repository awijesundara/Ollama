"""Chainlit callback registration only; implementation lives under src/."""

from typing import Any

import chainlit as cl
from chainlit.server import app as chainlit_server

from src.auth.ad_auth import (
    ADAuthenticator,
    AuthenticationRateLimited,
    LDAPConfig,
)
from src.auth.identity import (
    AuthenticationError,
    identity_from_google_claims,
    trusted_header_value,
)
from src.chat import handlers
from src.config import get_settings
from src.http_endpoints import register_http_endpoints
from src.logging_config import configure_logging
from src.memory.models import MemoryScope
from src.monitoring import ACTIVE_SESSIONS
from src.runtime import services

configure_logging()
register_http_endpoints(chainlit_server)
settings = get_settings()
data_layer_instance = services.data_layer
ad_authenticator = (
    ADAuthenticator(
        LDAPConfig(
            uri=settings.LDAP_URI or "",
            base_dn=settings.LDAP_BASE_DN or "",
            user_filter=settings.LDAP_USER_FILTER
            or "(&(objectClass=user)(userPrincipalName={username}))",
            ca_file=settings.LDAP_CA_FILE,
            connect_timeout=settings.LDAP_CONNECT_TIMEOUT,
            rate_limit=settings.LDAP_AUTH_RATE_LIMIT,
            rate_window_seconds=settings.LDAP_AUTH_RATE_WINDOW_SECONDS,
        )
    )
    if settings.AUTH_MODE == "ldap"
    else None
)


@cl.data_layer
def data_layer() -> Any:
    return data_layer_instance


@cl.password_auth_callback
async def password_auth(username: str, password: str) -> cl.User | None:
    if ad_authenticator is None:
        return None
    try:
        identity = await ad_authenticator.authenticate(username, password)
    except AuthenticationRateLimited:
        return None
    if identity is None:
        return None
    return cl.User(
        identifier=identity.user_identifier,
        metadata={
            "upn": identity.upn,
            "display_name": identity.display_name,
            "provider": "windows-ad",
        },
    )


@cl.header_auth_callback
def header_auth(headers: dict[str, str]) -> cl.User | None:
    if settings.AUTH_MODE != "header":
        return None
    try:
        identifier = trusted_header_value(
            headers.get(settings.TRUSTED_IDENTITY_HEADER),
            required=True,
        )
        upn = trusted_header_value(headers.get(settings.TRUSTED_UPN_HEADER))
        display_name = trusted_header_value(
            headers.get(settings.TRUSTED_DISPLAY_NAME_HEADER)
        )
    except AuthenticationError:
        return None
    if identifier is None:
        return None
    return cl.User(
        identifier=identifier,
        metadata={
            "upn": upn,
            "display_name": display_name,
            "provider": "trusted-proxy",
        },
    )


@cl.oauth_callback
def oauth_auth(
    provider_id: str,
    token: str,
    raw_user_data: dict[str, Any],
    default_user: cl.User,
) -> cl.User | None:
    del token, default_user
    if settings.AUTH_MODE != "google" or provider_id != "google":
        return None
    try:
        identity = identity_from_google_claims(
            raw_user_data,
            allowed_domain=settings.GOOGLE_ALLOWED_DOMAIN,
        )
    except AuthenticationError:
        return None
    return cl.User(
        identifier=identity.user_identifier,
        metadata={
            "upn": identity.upn,
            "display_name": identity.display_name,
            "provider": "google",
        },
    )


@cl.on_chat_start
async def chat_start() -> None:
    await handlers.on_chat_start()


@cl.on_chat_resume
async def chat_resume(thread: dict[str, Any]) -> None:
    await handlers.on_chat_resume(thread, data_layer_instance)


@cl.on_message
async def message(message: cl.Message) -> None:
    await handlers.on_message(message)


@cl.on_settings_update
async def settings_update(values: dict[str, Any]) -> None:
    await handlers.on_settings_update(values)


@cl.on_chat_end
def chat_end() -> None:
    ACTIVE_SESSIONS.dec()


@cl.action_callback("view_memories")
async def view_memories(_: cl.Action) -> None:
    await handlers.view_memories()


@cl.action_callback("export_memories")
async def export_memories(_: cl.Action) -> None:
    await handlers.export_memories()


@cl.action_callback("export_pdf")
async def export_pdf(_: cl.Action) -> None:
    await handlers.export_last_response_pdf()


@cl.action_callback("storage_location")
async def storage_location(_: cl.Action) -> None:
    await handlers.show_storage_location()


@cl.action_callback("add_global")
async def add_global(_: cl.Action) -> None:
    await handlers.add_memory_interactive(MemoryScope.GLOBAL)


@cl.action_callback("add_thread")
async def add_thread(_: cl.Action) -> None:
    await handlers.add_memory_interactive(MemoryScope.THREAD)


@cl.action_callback("delete_memory")
async def delete_memory(_: cl.Action) -> None:
    await handlers.delete_memory_interactive()


@cl.action_callback("clear_global")
async def clear_global(_: cl.Action) -> None:
    await handlers.clear_global_memories()


@cl.action_callback("clear_thread")
async def clear_thread(_: cl.Action) -> None:
    await handlers.clear_thread_memories()


@cl.action_callback("disable_memory")
async def disable_memory(_: cl.Action) -> None:
    await handlers.disable_memory()


@cl.on_shared_thread_view
async def deny_shared_thread(_: dict[str, Any], __: cl.User) -> bool:
    return False
