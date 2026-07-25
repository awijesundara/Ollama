import pytest
from pydantic import ValidationError

from src.config import Settings


def test_production_requires_secure_endpoints() -> None:
    with pytest.raises(ValidationError):
        Settings(
            APP_ENV="production",
            CHAINLIT_AUTH_SECRET="not-empty",
            CHAINLIT_URL="http://localhost:8000",
            LDAP_URI="ldap://directory",
            LDAP_BASE_DN="dc=example,dc=local",
            LDAP_CA_FILE="/etc/ca.pem",
        )


def test_automatic_memory_defaults_on() -> None:
    assert Settings(_env_file=None).MEMORY_AUTO_EXTRACTION is True


def test_metrics_are_disabled_by_default() -> None:
    assert Settings(_env_file=None).METRICS_ENABLED is False
