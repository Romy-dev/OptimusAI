import base64
import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    cursor: str | None = None
    limit: int = Field(default=20, ge=1, le=100)


class PaginatedResponse(BaseModel):
    data: list
    meta: dict

    @classmethod
    def create(cls, items: list, limit: int, cursor_field: str = "id") -> "PaginatedResponse":
        has_more = len(items) > limit
        if has_more:
            items = items[:limit]

        next_cursor = None
        if has_more and items:
            last_item = items[-1]
            raw = getattr(last_item, cursor_field, None)
            if raw is not None:
                next_cursor = base64.b64encode(str(raw).encode()).decode()

        return cls(
            data=items,
            meta={
                "has_more": has_more,
                "next_cursor": next_cursor,
                "count": len(items),
            },
        )

    @staticmethod
    def decode_cursor(cursor: str) -> str:
        return base64.b64decode(cursor.encode()).decode()
