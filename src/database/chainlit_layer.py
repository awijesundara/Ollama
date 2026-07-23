from typing import Any, cast

from chainlit.data.sql_alchemy import SQLAlchemyDataLayer
from chainlit.step import StepDict

from src.security.secret_detection import detect_secret


class OwnershipCheckingDataLayer(SQLAlchemyDataLayer):
    """Chainlit persistence plus explicit thread ownership verification."""

    async def create_step(self, step_dict: StepDict) -> None:
        sanitized = dict(step_dict)
        for field in ("input", "output"):
            value = sanitized.get(field)
            if isinstance(value, str) and detect_secret(value):
                sanitized[field] = "[REDACTED: secret removed]"
        await super().create_step(cast(StepDict, sanitized))

    async def update_step(self, step_dict: StepDict) -> None:
        sanitized = dict(step_dict)
        for field in ("input", "output"):
            value = sanitized.get(field)
            if isinstance(value, str) and detect_secret(value):
                sanitized[field] = "[REDACTED: secret removed]"
        await super().update_step(cast(StepDict, sanitized))

    async def require_thread_owner(
        self, thread_id: str, user_identifier: str
    ) -> dict[str, Any]:
        author = await self.get_thread_author(thread_id)
        if author != user_identifier:
            raise PermissionError("Thread is unavailable")
        thread = await self.get_thread(thread_id)
        if thread is None:
            raise PermissionError("Thread is unavailable")
        return dict(thread)


def create_chainlit_data_layer(database_url: str) -> OwnershipCheckingDataLayer:
    conninfo = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return OwnershipCheckingDataLayer(conninfo=conninfo)
