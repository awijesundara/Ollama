import base64
from typing import cast

import pytest

pytest.importorskip("cryptography")
pytest.importorskip("chainlit")

from chainlit.step import StepDict
from chainlit.types import Pagination, ThreadFilter
from chainlit.user import User

from src.database.encrypted_file_layer import EncryptedFileDataLayer
from src.storage.encrypted_store import EncryptedUserStore


@pytest.mark.asyncio
async def test_encrypted_layer_persists_and_lists_user_history(tmp_path) -> None:
    key = base64.b64encode(b"h" * 32).decode()
    layer = EncryptedFileDataLayer(EncryptedUserStore(str(tmp_path), key))
    user = await layer.create_user(User(identifier="alice", metadata={"role": "user"}))

    await layer.update_thread(
        "thread-1",
        name="Private chat",
        user_id=user.id,
        metadata={"source": "test"},
    )
    await layer._upsert_step(
        cast(
            StepDict,
            {
                "id": "step-1",
                "threadId": "thread-1",
                "name": "user",
                "type": "user_message",
                "input": "hello",
                "output": "",
                "createdAt": "2026-01-01T00:00:00+00:00",
            },
        )
    )

    thread = await layer.get_thread("thread-1")
    assert thread is not None
    assert thread["userIdentifier"] == "alice"
    assert thread["steps"][0]["input"] == "hello"

    page = await layer.list_threads(
        Pagination(first=10, cursor=None),
        ThreadFilter(userId=user.id),
    )
    assert [item["id"] for item in page.data] == ["thread-1"]


@pytest.mark.asyncio
async def test_encrypted_layer_rejects_cross_user_thread_access(tmp_path) -> None:
    key = base64.b64encode(b"h" * 32).decode()
    layer = EncryptedFileDataLayer(EncryptedUserStore(str(tmp_path), key))
    alice = await layer.create_user(User(identifier="alice", metadata={}))
    await layer.create_user(User(identifier="bob", metadata={}))
    await layer.update_thread("thread-1", user_id=alice.id)

    with pytest.raises(PermissionError):
        await layer.require_thread_owner("thread-1", "bob")
