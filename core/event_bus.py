import asyncio
import logging
from typing import Any, Callable, Dict, List, Coroutine
from core.schema import EventType

logger = logging.getLogger(__name__)

class EventBus:
    """Decoupled asynchronous communication system for multi-agent coordination."""

    def __init__(self) -> None:
        """Initializes the subscriber registry."""
        self._subscribers: Dict[EventType, List[Callable[[Any], Coroutine[Any, Any, None]]]] = {
            e: [] for e in EventType
        }

    def subscribe(self, event_type: EventType, handler: Callable[[Any], Coroutine[Any, Any, None]]) -> None:
        """
        Registers an async callback for a specific event.

        Args:
            event_type: The event type to observe.
            handler: Async function to execute on event broadcast.
        """
        if handler not in self._subscribers[event_type]:
            self._subscribers[event_type].append(handler)
            logger.debug(f"Subscribed {handler.__name__} to {event_type.value}")

    async def publish(self, event_type: EventType, payload: Any) -> None:
        """
        Broadcasts an event to all registered subscribers.

        Args:
            event_type: Type of event being published.
            payload: Data associated with the event.
        """
        logger.info(f"Event published: {event_type.value}")
        handlers = self._subscribers.get(event_type, [])
        if handlers:
            await asyncio.gather(*(h(payload) for h in handlers), return_exceptions=True)