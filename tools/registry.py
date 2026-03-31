import logging
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class ToolMetadata(BaseModel):
    """Schema for tool discovery and documentation."""
    name: str
    description: str
    parameters: Dict[str, Any]
    category: str

class ToolRegistry:
    """
    Central repository for all agent-accessible tools.
    Supports permissioning and structured metadata retrieval.
    """

    def __init__(self) -> None:
        self._tools: Dict[str, Callable] = {}
        self._metadata: Dict[str, ToolMetadata] = {}

    def register(self, metadata: ToolMetadata):
        """
        Decorator-ready registration method.
        
        Args:
            metadata: Structured info about what the tool does.
        """
        def decorator(func: Callable):
            self._tools[metadata.name] = func
            self._metadata[metadata.name] = metadata
            return func
        return decorator

    def get_tool(self, name: str) -> Optional[Callable]:
        """Retrieves the executable function for a tool."""
        return self._tools.get(name)

    def list_tools(self, category: Optional[str] = None) -> List[ToolMetadata]:
        """Returns metadata for all tools, optionally filtered by category."""
        if category:
            return [m for m in self._metadata.values() if m.category == category]
        return list(self._metadata.values())

    def execute(self, name: str, **kwargs) -> Any:
        """Executes a tool by name with provided arguments."""
        tool_func = self.get_tool(name)
        if not tool_func:
            raise ValueError(f"Tool '{name}' not found in registry.")
        
        logger.info(f"Executing tool: {name} with args: {kwargs}")
        try:
            return tool_func(**kwargs)
        except Exception as e:
            logger.error(f"Error executing {name}: {str(e)}")
            raise