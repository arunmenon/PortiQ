"""EventHandlerRegistry — central registry for event handlers."""

import logging
from collections import defaultdict
from collections.abc import Callable

logger = logging.getLogger(__name__)


class EventHandlerRegistry:
    """Singleton-style registry for event handlers.

    Handlers are plain callables that accept a payload dict.
    Multiple handlers can be registered for the same event_type.
    """

    _handlers: dict[str, list[Callable]] = defaultdict(list)

    @classmethod
    def register(cls, event_type: str, handler: Callable) -> None:
        """Register a handler for a given event type."""
        cls._handlers[event_type].append(handler)
        logger.info("Registered handler %s for event type %s", handler.__name__, event_type)

    @classmethod
    def get_handlers(cls, event_type: str) -> list[Callable]:
        """Return all handlers registered for the given event type."""
        return cls._handlers.get(event_type, [])

    @classmethod
    def dispatch(cls, event_type: str, payload: dict) -> list[dict]:
        """Dispatch an event to all registered handlers.

        Returns a list of result dicts with handler name and status.
        Errors are logged and captured but do not stop other handlers.
        """
        results = []
        for handler in cls.get_handlers(event_type):
            try:
                handler(payload)
                results.append({"handler": handler.__name__, "status": "ok"})
            except Exception as exc:
                logger.exception(
                    "Handler %s failed for event type %s", handler.__name__, event_type
                )
                results.append({
                    "handler": handler.__name__,
                    "status": "error",
                    "error": str(exc),
                })
        return results

    @classmethod
    def clear(cls) -> None:
        """Remove all registered handlers. Useful for testing."""
        cls._handlers.clear()
