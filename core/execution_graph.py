import logging
from typing import List, Dict, Optional, Any
from core.schema import WorkflowGraph, TaskNode, NodeStatus

logger = logging.getLogger(__name__)

class ExecutionGraphEngine:
    """Manages state transitions and dependency resolution for the Task DAG."""

    def __init__(self, graph: WorkflowGraph) -> None:
        """
        Args:
            graph: The WorkflowGraph to manage.
        """
        self._graph = graph

    def get_runnable_nodes(self) -> List[TaskNode]:
        """
        Identifies nodes that are ready to execute (dependencies satisfied).

        Returns:
            List of TaskNode objects with status 'READY'.
        """
        runnable = []
        for node in self._graph.nodes.values():
            if node.status != NodeStatus.PENDING:
                continue
            
            # A node is ready if all dependencies have status COMPLETED
            if all(self._graph.nodes[d].status == NodeStatus.COMPLETED for d in node.dependencies):
                node.status = NodeStatus.READY
                runnable.append(node)
        return runnable

    def update_node(self, node_id: str, status: NodeStatus, output: Optional[Dict[str, Any]] = None, error: Optional[str] = None) -> None:
        """
        Updates the status and data of a specific node.

        Args:
            node_id: ID of node to update.
            status: New execution status.
            output: Result data if completed.
            error: Error message if failed.
        """
        if node_id not in self._graph.nodes:
            logger.error(f"Node {node_id} not found in graph.")
            return

        node = self._graph.nodes[node_id]
        node.status = status
        if output:
            node.output_data = output
        if error:
            node.error_message = error
        
        logger.info(f"Node {node_id} transitioned to {status.value}")

    @property
    def is_finished(self) -> bool:
        """Checks if the entire graph has reached a terminal state."""
        return all(n.status in [NodeStatus.COMPLETED, NodeStatus.FAILED, NodeStatus.SKIPPED] for n in self._graph.nodes.values())

    @property
    def has_errors(self) -> bool:
        """Returns True if any node failed."""
        return any(n.status == NodeStatus.FAILED for n in self._graph.nodes.values())