from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from typing import Any, cast
from uuid import NAMESPACE_URL, uuid4, uuid5

from chainlit.data import BaseDataLayer, queue_until_user_message
from chainlit.element import ElementDict
from chainlit.step import StepDict
from chainlit.types import (
    Feedback,
    PageInfo,
    PaginatedResponse,
    Pagination,
    ThreadDict,
    ThreadFilter,
)
from chainlit.user import PersistedUser, User

from src.security.secret_detection import detect_secret
from src.storage.encrypted_store import Document, EncryptedUserStore


class EncryptedFileDataLayer(BaseDataLayer):
    """Chainlit history stored inside per-user authenticated encryption files."""

    def __init__(self, store: EncryptedUserStore) -> None:
        self.store = store

    async def get_user(self, identifier: str) -> PersistedUser | None:
        document = await self.store.read_user(identifier)
        user = document["user"]
        if not user.get("id"):
            return None
        return PersistedUser(
            id=user["id"],
            identifier=user["identifier"],
            metadata=user.get("metadata", {}),
            createdAt=user["createdAt"],
        )

    async def create_user(self, user: User) -> PersistedUser:
        if not user.identifier:
            raise ValueError("Authenticated user identifier is required")
        created_at = datetime.now(UTC).isoformat()
        user_id = str(uuid5(NAMESPACE_URL, f"chainlit:{user.identifier}"))

        def create(document: Document) -> dict[str, Any]:
            current = cast(dict[str, Any], document["user"])
            current.update(
                {
                    "id": current.get("id") or user_id,
                    "identifier": user.identifier,
                    "metadata": {**current.get("metadata", {}), **user.metadata},
                    "createdAt": current.get("createdAt") or created_at,
                }
            )
            return dict(current)

        saved = await self.store.mutate_user(user.identifier, create)
        return PersistedUser(
            id=saved["id"],
            identifier=saved["identifier"],
            metadata=saved["metadata"],
            createdAt=saved["createdAt"],
        )

    async def upsert_feedback(self, feedback: Feedback) -> str:
        value = _to_dict(feedback)
        thread_id = str(value.get("threadId") or "")
        owner = await self._require_owner(thread_id)
        feedback_id = str(value.get("id") or uuid4())
        value["id"] = feedback_id

        def upsert(document: Document) -> None:
            thread = document["threads"][thread_id]
            thread.setdefault("feedbacks", {})[feedback_id] = value

        await self.store.mutate_user(owner, upsert)
        return feedback_id

    async def delete_feedback(self, feedback_id: str) -> bool:
        for owner in await self.store.all_user_identifiers():
            document = await self.store.read_user(owner)
            for thread_id, thread in document["threads"].items():
                if feedback_id in thread.get("feedbacks", {}):

                    def delete(
                        current: Document, target_thread: str = thread_id
                    ) -> bool:
                        return (
                            current["threads"][target_thread]
                            .setdefault("feedbacks", {})
                            .pop(feedback_id, None)
                            is not None
                        )

                    return await self.store.mutate_user(owner, delete)
        return False

    async def create_element(self, element_dict: ElementDict) -> None:
        value = dict(element_dict)
        thread_id = str(value.get("threadId") or "")
        owner = await self._require_owner(thread_id)
        element_id = str(value["id"])

        def create(document: Document) -> None:
            document["threads"][thread_id].setdefault("elements", {})[element_id] = (
                value
            )

        await self.store.mutate_user(owner, create)

    async def get_element(self, thread_id: str, element_id: str) -> ElementDict | None:
        owner = await self._require_owner(thread_id)
        document = await self.store.read_user(owner)
        value = document["threads"][thread_id].get("elements", {}).get(element_id)
        return cast(ElementDict, value) if value else None

    async def delete_element(self, element_id: str) -> None:
        for owner in await self.store.all_user_identifiers():
            document = await self.store.read_user(owner)
            for thread_id, thread in document["threads"].items():
                if element_id in thread.get("elements", {}):

                    def delete(
                        current: Document, target_thread: str = thread_id
                    ) -> None:
                        current["threads"][target_thread].setdefault(
                            "elements", {}
                        ).pop(element_id, None)

                    await self.store.mutate_user(owner, delete)
                    return

    @queue_until_user_message()
    async def create_step(self, step_dict: StepDict) -> None:
        await self._upsert_step(step_dict)

    @queue_until_user_message()
    async def update_step(self, step_dict: StepDict) -> None:
        await self._upsert_step(step_dict)

    async def _upsert_step(self, step_dict: StepDict) -> None:
        value = _sanitize_step(step_dict)
        thread_id = str(value.get("threadId") or "")
        owner = await self._require_owner(thread_id)
        step_id = str(value["id"])

        def upsert(document: Document) -> None:
            document["threads"][thread_id].setdefault("steps", {})[step_id] = value
            document["threads"][thread_id]["updatedAt"] = datetime.now(UTC).isoformat()

        await self.store.mutate_user(owner, upsert)

    async def delete_step(self, step_id: str) -> None:
        for owner in await self.store.all_user_identifiers():
            document = await self.store.read_user(owner)
            for thread_id, thread in document["threads"].items():
                if step_id in thread.get("steps", {}):

                    def delete(
                        current: Document, target_thread: str = thread_id
                    ) -> None:
                        current["threads"][target_thread].setdefault("steps", {}).pop(
                            step_id, None
                        )

                    await self.store.mutate_user(owner, delete)
                    return

    async def get_thread_author(self, thread_id: str) -> str:
        return await self._require_owner(thread_id)

    async def delete_thread(self, thread_id: str) -> None:
        owner = await self._require_owner(thread_id)

        def delete(document: Document) -> None:
            document["threads"].pop(thread_id, None)
            document["summaries"].pop(thread_id, None)

        await self.store.mutate_user(owner, delete)

    async def list_threads(
        self,
        pagination: Pagination,
        filters: ThreadFilter,
    ) -> PaginatedResponse[ThreadDict]:
        if not filters.userId:
            raise ValueError("userId is required")
        owner = await self.store.find_user_by_id(filters.userId)
        if owner is None:
            return _empty_page()
        document = await self.store.read_user(owner)
        threads = list(document["threads"].values())
        if filters.search:
            query = filters.search.casefold()
            threads = [
                thread
                for thread in threads
                if query in str(thread.get("name") or "").casefold()
                or any(
                    query
                    in (f"{step.get('input', '')} {step.get('output', '')}").casefold()
                    for step in thread.get("steps", {}).values()
                )
            ]
        threads.sort(
            key=lambda thread: str(
                thread.get("updatedAt") or thread.get("createdAt") or ""
            ),
            reverse=True,
        )
        if pagination.cursor:
            threads = [
                thread
                for thread in threads
                if str(thread.get("updatedAt") or "") < pagination.cursor
            ]
        page = threads[: pagination.first + 1]
        has_next = len(page) > pagination.first
        page = page[: pagination.first]
        data = [cast(ThreadDict, _thread_header(thread)) for thread in page]
        return PaginatedResponse(
            data=data,
            pageInfo=PageInfo(
                hasNextPage=has_next,
                startCursor=(str(page[0].get("updatedAt")) if page else None),
                endCursor=(str(page[-1].get("updatedAt")) if page else None),
            ),
        )

    async def get_thread(self, thread_id: str) -> ThreadDict | None:
        owner = await self.store.find_thread_owner(thread_id)
        if owner is None:
            return None
        document = await self.store.read_user(owner)
        thread = document["threads"][thread_id]
        feedback_by_step = {
            str(item.get("forId")): item
            for item in thread.get("feedbacks", {}).values()
        }
        steps = []
        for step in thread.get("steps", {}).values():
            value = dict(step)
            if str(value["id"]) in feedback_by_step:
                value["feedback"] = feedback_by_step[str(value["id"])]
            steps.append(value)
        steps.sort(key=lambda item: str(item.get("createdAt") or ""))
        return cast(
            ThreadDict,
            {
                **_thread_header(thread),
                "steps": steps,
                "elements": list(thread.get("elements", {}).values()),
            },
        )

    async def update_thread(
        self,
        thread_id: str,
        name: str | None = None,
        user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> None:
        owner = (
            await self.store.find_user_by_id(user_id)
            if user_id
            else await self.store.find_thread_owner(thread_id)
        )
        if owner is None:
            raise PermissionError("Thread owner is unavailable")
        now = datetime.now(UTC).isoformat()

        def update(document: Document) -> None:
            current = document["threads"].setdefault(
                thread_id,
                {
                    "id": thread_id,
                    "createdAt": now,
                    "updatedAt": now,
                    "name": None,
                    "userId": document["user"]["id"],
                    "userIdentifier": owner,
                    "tags": [],
                    "metadata": {},
                    "steps": {},
                    "elements": {},
                    "feedbacks": {},
                },
            )
            if name is not None:
                current["name"] = name
            if metadata is not None:
                current["metadata"] = metadata
                if metadata.get("thread_name"):
                    current["name"] = metadata["thread_name"]
            if tags is not None:
                current["tags"] = tags
            current["updatedAt"] = now

        await self.store.mutate_user(owner, update)

    async def delete_user_session(self, id: str) -> bool:
        return True

    async def get_favorite_steps(self, user_id: str) -> list[StepDict]:
        return []

    async def close(self) -> None:
        return None

    async def build_debug_url(self) -> str:
        return ""

    async def require_thread_owner(
        self, thread_id: str, user_identifier: str
    ) -> dict[str, Any]:
        owner = await self.get_thread_author(thread_id)
        if not hmac_compare(owner, user_identifier):
            raise PermissionError("Thread is unavailable")
        thread = await self.get_thread(thread_id)
        if thread is None:
            raise PermissionError("Thread is unavailable")
        return dict(thread)

    async def _require_owner(self, thread_id: str) -> str:
        if not thread_id:
            raise PermissionError("Thread is unavailable")
        owner = await self.store.find_thread_owner(thread_id)
        if owner is None:
            raise PermissionError("Thread is unavailable")
        return owner


def _sanitize_step(step: StepDict) -> dict[str, Any]:
    value = dict(step)
    for field in ("input", "output"):
        content = value.get(field)
        if isinstance(content, str) and detect_secret(content):
            value[field] = "[REDACTED: secret removed]"
    return value


def _thread_header(thread: dict[str, Any]) -> dict[str, Any]:
    return {
        key: thread.get(key)
        for key in (
            "id",
            "createdAt",
            "updatedAt",
            "name",
            "userId",
            "userIdentifier",
            "tags",
            "metadata",
        )
    }


def _empty_page() -> PaginatedResponse[ThreadDict]:
    return PaginatedResponse(
        data=[],
        pageInfo=PageInfo(
            hasNextPage=False,
            startCursor=None,
            endCursor=None,
        ),
    )


def _to_dict(value: object) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return dict(value.model_dump())
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    return dict(vars(value))


def hmac_compare(left: str, right: str) -> bool:
    import hmac

    return hmac.compare_digest(left.encode(), right.encode())
