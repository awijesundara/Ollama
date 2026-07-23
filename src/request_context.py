import contextvars
import logging
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RequestContext:
    correlation_id: str = ""
    thread_id: str = ""
    user_hash: str = ""


_context: contextvars.ContextVar[RequestContext] = contextvars.ContextVar(
    "request_context", default=RequestContext()
)


def bind_context(
    *, correlation_id: str = "", thread_id: str = "", user_hash: str = ""
) -> None:
    _context.set(RequestContext(correlation_id, thread_id, user_hash))


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        current = _context.get()
        record.correlation_id = current.correlation_id
        record.thread_id = current.thread_id
        record.user_hash = current.user_hash
        return True

