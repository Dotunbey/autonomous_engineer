from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field, validator
from uuid import uuid4

class EventType(str, Enum):
    """Supported system-wide event types."""
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    PLAN_CREATED = "plan.created"
    PLAN_UPDATED = "plan.updated"
    SYSTEM_LOG = "system.log"

class NodeStatus(str, Enum):
    """Execution status for individual DAG nodes."""
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class TaskNode(BaseModel):
    """A single unit of work within the execution graph."""
    node_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    description: str
    agent_role: str
    dependencies: Set[str] = Field(default_factory=set)
    status: NodeStatus = NodeStatus.PENDING
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)

class WorkflowGraph(BaseModel):
    """The Directed Acyclic Graph (DAG) representing the full engineering plan."""
    graph_id: str = Field(default_factory=lambda: str(uuid4()))
    nodes: Dict[str, TaskNode] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @validator("nodes")
    def validate_dag(cls, v: Dict[str, TaskNode]) -> Dict[str, TaskNode]:
        """Ensures the graph contains no cycles."""
        def has_cycle(node_id: str, visited: Set[str], stack: Set[str]) -> bool:
            visited.add(node_id)
            stack.add(node_id)
            for dep in v.get(node_id).dependencies:
                if dep not in visited:
                    if has_cycle(dep, visited, stack):
                        return True
                elif dep in stack:
                    return True
            stack.remove(node_id)
            return False

        visited, stack = set(), set()
        for node_id in v:
            if node_id not in visited:
                if has_cycle(node_id, visited, stack):
                    raise ValueError(f"Cycle detected in workflow graph involving node {node_id}")
        return v