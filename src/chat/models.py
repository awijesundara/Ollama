from datetime import datetime

from pydantic import BaseModel, Field

from src.ollama.models import ChatMessage


class ThreadSummary(BaseModel):
    thread_id: str
    user_identifier: str
    summary_text: str
    summarized_through_message_id: str | None = None
    summarized_message_count: int = 0
    created_at: datetime
    updated_at: datetime


class SummaryOutput(BaseModel):
    summary: str = Field(min_length=1, max_length=8000)


class ConversationState(BaseModel):
    thread_id: str
    messages: list[ChatMessage] = Field(default_factory=list)
    summary: ThreadSummary | None = None
