import asyncio
import ssl
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock
from uuid import UUID

from ldap3 import ALL, Connection, Server, Tls
from ldap3.core.exceptions import LDAPException
from ldap3.utils.conv import escape_filter_chars

from src.auth.identity import AuthenticatedIdentity


@dataclass(frozen=True, slots=True)
class LDAPConfig:
    uri: str
    base_dn: str
    user_filter: str = "(&(objectClass=user)(userPrincipalName={username}))"
    ca_file: str | None = None
    connect_timeout: float = 10
    rate_limit: int = 5
    rate_window_seconds: int = 60


class AuthenticationRateLimited(RuntimeError):
    pass


class ADAuthenticator:
    """LDAPS bind authentication. Passwords exist only for the bind call."""

    def __init__(self, config: LDAPConfig) -> None:
        self._config = config
        self._attempts: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    async def authenticate(
        self, username: str, password: str
    ) -> AuthenticatedIdentity | None:
        if not username.strip() or not password:
            return None
        self._check_rate_limit(username.casefold())
        return await asyncio.to_thread(self._bind, username, password)

    def _check_rate_limit(self, key: str) -> None:
        now = time.monotonic()
        cutoff = now - self._config.rate_window_seconds
        with self._lock:
            attempts = self._attempts[key]
            while attempts and attempts[0] < cutoff:
                attempts.popleft()
            if len(attempts) >= self._config.rate_limit:
                raise AuthenticationRateLimited("Too many authentication attempts")
            attempts.append(now)

    def _bind(self, username: str, password: str) -> AuthenticatedIdentity | None:
        host = self._config.uri.removeprefix("ldaps://").split(":", 1)[0]
        tls = Tls(
            validate=ssl.CERT_REQUIRED,
            ca_certs_file=self._config.ca_file,
            version=ssl.PROTOCOL_TLS_CLIENT,
        )
        server = Server(
            host,
            port=636,
            use_ssl=True,
            tls=tls,
            get_info=ALL,
            connect_timeout=self._config.connect_timeout,
        )
        safe_username = escape_filter_chars(username.strip())
        search_filter = self._config.user_filter.format(username=safe_username)
        try:
            with Connection(
                server,
                user=username,
                password=password,
                auto_bind=True,
                raise_exceptions=True,
                receive_timeout=self._config.connect_timeout,
            ) as connection:
                if not connection.search(
                    self._config.base_dn,
                    search_filter,
                    attributes=[
                        "objectGUID",
                        "userPrincipalName",
                        "displayName",
                        "department",
                    ],
                    size_limit=2,
                ):
                    return None
                if len(connection.entries) != 1:
                    return None
                entry = connection.entries[0]
                raw_guid = entry.entry_raw_attributes.get("objectGUID", [])
                if not raw_guid:
                    return None
                identifier = str(UUID(bytes_le=raw_guid[0]))
                return AuthenticatedIdentity(
                    user_identifier=identifier,
                    upn=str(entry.userPrincipalName.value or "") or None,
                    display_name=str(entry.displayName.value or "") or None,
                )
        except LDAPException:
            return None

