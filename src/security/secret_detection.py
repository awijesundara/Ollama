import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SecretMatch:
    kind: str


_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("bearer_token", re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{12,}", re.I)),
    ("authentication_header", re.compile(r"\bAuthorization\s*:", re.I)),
    ("cloud_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    (
        "connection_string",
        re.compile(r"\b(?:postgres(?:ql)?|mysql)://[^:\s]+:[^@\s]+@"),
    ),
    (
        "credential_assignment",
        re.compile(
            r"\b(?:password|passwd|passphrase|api[_ -]?key|secret|session[_ -]?cookie)"
            r"\s*[:=]\s*\S+",
            re.I,
        ),
    ),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]+")),
    ("credit_card", re.compile(r"\b(?:\d[ -]*?){13,19}\b")),
    (
        "one_time_password",
        re.compile(r"\b(?:otp|recovery code)\s*[:=]\s*\d{6,12}\b", re.I),
    ),
)


def detect_secret(text: str) -> SecretMatch | None:
    for kind, pattern in _PATTERNS:
        if pattern.search(text):
            return SecretMatch(kind=kind)
    return None
