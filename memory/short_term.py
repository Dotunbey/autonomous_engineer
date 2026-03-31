#!memory/short_term.py
import logging
from collections import deque
from typing import Any, Dict, List
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class ActionLog(BaseModel):
    """Schema for a single short-term event."""
    action_type: str
    details: str
    success: bool
    context: Dict[str, Any] = Field(default_factory=dict)

class ShortTermMemory:
    """
    Maintains a sliding window of recent agent actions, observations, and state changes.
    Prevents token limit overflow by discarding the oldest context.
    """

    def __init__(self, max_capacity: int = 20):
        """
        Initializes the short term context window.

        Args:
            max_capacity: The maximum number of actions to retain.
        """
        self._capacity = max_capacity
        self._buffer: deque[ActionLog] = deque(maxlen=max_capacity)

    @property
    def capacity(self) -> int:
        """Returns the maximum capacity of the memory buffer."""
        return self._capacity

    def add_event(self, action_type: str, details: str, success: bool, context: Dict[str, Any] = None) -> None:
        """
        Records a new event into the rolling buffer.

        Args:
            action_type: Category of the action (e.g., 'TOOL_CALL', 'PLAN_UPDATE').
            details: Human-readable description of what happened.
            success: Whether the action completed without errors.
            context: Additional state data.
        """
        log = ActionLog(
            action_type=action_type,
            details=details,
            success=success,
            context=context or {}
        )
        self._buffer.append(log)
        logger.debug(f"Recorded short term event: [{action_type}] {details[:50]}...")

    def get_recent_context(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieves the most recent events formatted for LLM context injection.

        Args:
            limit: How many recent items to fetch.

        Returns:
            A list of dictionary representations of the recent logs.
        """
        items = list(self._buffer)[-limit:]
        return [item.dict() for item in items]

    def clear(self) -> None:
        """Wipes the short term memory buffer."""
        self._buffer.clear()
        logger.info("Short term memory cleared.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    stm = ShortTermMemory(max_capacity=3)
    stm.add_event("TOOL_CALL", "Ran pytest on auth.py", False, {"error": "Missing import"})
    stm.add_event("FILE_EDIT", "Added import PyJWT to auth.py", True)
    stm.add_event("TOOL_CALL", "Ran pytest on auth.py", True)
    stm.add_event("PLAN_UPDATE", "Auth module complete, moving to API layer", True)
    
    # Notice the first event is dropped because max_capacity=3
    recent = stm.get_recent_context(limit=10)
    for r in recent:
        print(r)