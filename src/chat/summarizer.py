from typing import Sequence

import asyncpg

from src.chat.models import SummaryOutput, ThreadSummary
from src.ollama.client import OllamaService
from src.ollama.models import ChatMessage
from src.security.secret_detection import detect_secret


class ThreadSummaryRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get(
        self, user_identifier: str, thread_id: str
    ) -> ThreadSummary | None:
        row = await self._pool.fetchrow(
            """
            SELECT * FROM thread_summaries
            WHERE user_identifier = $1 AND thread_id = $2
            """,
            user_identifier,
            thread_id,
        )
        return ThreadSummary.model_validate(dict(row)) if row else None

    async def upsert(
        self,
        user_identifier: str,
        thread_id: str,
        summary: str,
        through_message_id: str | None,
        count: int,
    ) -> ThreadSummary:
        row = await self._pool.fetchrow(
            """
            INSERT INTO thread_summaries (
                thread_id, user_identifier, summary_text,
                summarized_through_message_id, summarized_message_count
            ) VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (thread_id) DO UPDATE SET
                summary_text = EXCLUDED.summary_text,
                summarized_through_message_id =
                    EXCLUDED.summarized_through_message_id,
                summarized_message_count = EXCLUDED.summarized_message_count,
                updated_at = NOW()
            WHERE thread_summaries.user_identifier = EXCLUDED.user_identifier
            RETURNING *
            """,
            thread_id,
            user_identifier,
            summary,
            through_message_id,
            count,
        )
        if row is None:
            raise PermissionError("Thread summary ownership mismatch")
        return ThreadSummary.model_validate(dict(row))


class ThreadSummarizer:
    def __init__(
        self,
        repository: ThreadSummaryRepository,
        ollama: OllamaService,
        trigger_messages: int,
        recent_messages: int,
    ) -> None:
        self._repository = repository
        self._ollama = ollama
        self._trigger = trigger_messages
        self._recent = recent_messages

    async def maybe_update(
        self,
        user_identifier: str,
        thread_id: str,
        messages: Sequence[ChatMessage],
        last_message_id: str | None,
    ) -> ThreadSummary | None:
        current = await self._repository.get(user_identifier, thread_id)
        already = current.summarized_message_count if current else 0
        if len(messages) - already < self._trigger:
            return current
        unsummarized_end = max(already, len(messages) - self._recent)
        older = list(messages[already:unsummarized_end])
        if not older:
            return current
        previous = current.summary_text if current else "(none)"
        transcript = "\n".join(
            f"{message.role}: {message.content}"
            for message in older
            if detect_secret(message.content) is None
        )
        if not transcript:
            return current
        prompt = (
            "Update the factual conversation summary. Retain goals, confirmed "
            "constraints, decisions, pending tasks, errors, paths and hosts. "
            "Exclude secrets, full logs, reasoning and guesses.\n\n"
            f"Previous summary:\n{previous}\n\nNew messages:\n{transcript}"
        )
        result = await self._ollama.structured_chat(
            [ChatMessage(role="user", content=prompt)], SummaryOutput
        )
        if detect_secret(result.summary):
            return current
        return await self._repository.upsert(
            user_identifier,
            thread_id,
            result.summary,
            last_message_id,
            already + len(older),
        )
