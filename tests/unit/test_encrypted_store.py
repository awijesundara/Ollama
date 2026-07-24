import base64

import pytest

pytest.importorskip("cryptography")

from src.storage.encrypted_store import EncryptedFileError, EncryptedUserStore


def key() -> str:
    return base64.b64encode(b"k" * 32).decode()


@pytest.mark.asyncio
async def test_user_document_is_encrypted_and_location_is_opaque(tmp_path) -> None:
    store = EncryptedUserStore(str(tmp_path), key())
    await store.mutate_user(
        "alice@example.local",
        lambda document: document["preferences"].update({"memory_enabled": False}),
    )

    path = store.user_path("alice@example.local")
    payload = path.read_bytes()
    assert path.suffix == ".enc"
    assert "alice" not in path.name
    assert b"alice@example.local" not in payload
    assert b"memory_enabled" not in payload
    assert (await store.read_user("alice@example.local"))["preferences"][
        "memory_enabled"
    ] is False


@pytest.mark.asyncio
async def test_tampering_is_detected(tmp_path) -> None:
    store = EncryptedUserStore(str(tmp_path), key())
    await store.mutate_user("alice", lambda document: None)
    path = store.user_path("alice")
    payload = bytearray(path.read_bytes())
    payload[-1] ^= 1
    path.write_bytes(payload)

    with pytest.raises(EncryptedFileError):
        await store.read_user("alice")


@pytest.mark.asyncio
async def test_users_have_separate_envelopes(tmp_path) -> None:
    store = EncryptedUserStore(str(tmp_path), key())
    await store.mutate_user("alice", lambda document: None)
    await store.mutate_user("bob", lambda document: None)
    assert store.user_path("alice") != store.user_path("bob")
    assert len(list(tmp_path.glob("*.enc"))) == 2
