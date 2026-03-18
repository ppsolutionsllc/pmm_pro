from __future__ import annotations

from contextvars import ContextVar


request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter:
    def filter(self, record) -> bool:  # pragma: no cover - std logging hook
        record.request_id = request_id_ctx.get("-")
        return True
