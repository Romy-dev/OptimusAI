"""Internal event bus for decoupled communication between services."""

import asyncio
from collections import defaultdict
from collections.abc import Callable, Coroutine
from typing import Any

import structlog

logger = structlog.get_logger()

EventHandler = Callable[..., Coroutine[Any, Any, None]]


class EventBus:
    """Simple in-process async event bus.

    Usage:
        bus = EventBus()
        bus.subscribe("post.published", handle_post_published)
        await bus.emit("post.published", post_id=post.id, tenant_id=tenant.id)
    """

    def __init__(self):
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        self._handlers[event_type].remove(handler)

    async def emit(self, event_type: str, **kwargs) -> None:
        handlers = self._handlers.get(event_type, [])
        for handler in handlers:
            try:
                await handler(**kwargs)
            except Exception:
                logger.exception(
                    "event_handler_error",
                    event_type=event_type,
                    handler=handler.__name__,
                )


# Global event bus instance
event_bus = EventBus()
