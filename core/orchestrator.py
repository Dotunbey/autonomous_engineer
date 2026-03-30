import asyncio
import logging
from typing import Any, Dict, Optional
from core.schema import EventType, NodeStatus, WorkflowGraph
from core.event_bus import EventBus
from core.execution_graph import ExecutionGraphEngine
from core.planner import HierarchicalPlanner

logger = logging.getLogger(__name__)

class Orchestrator:
    """Main execution loop that coordinates planning, state management, and agents."""

    def __init__(self, workspace: str, planner: HierarchicalPlanner, bus: EventBus) -> None:
        self.workspace = workspace
        self.planner = planner
        self.bus = bus
        self.engine: Optional[ExecutionGraphEngine] = None

    async def run(self, goal: str) -> Dict[str, Any]:
        """
        Starts the autonomous engineering process.

        Args:
            goal: The task to achieve.

        Returns:
            The final output state.
        """
        logger.info(f"Starting orchestration for: {goal}")
        
        # 1. Create the Graph
        graph = await self.planner.create_plan(goal, {"workspace": self.workspace})
        self.engine = ExecutionGraphEngine(graph)
        await self.bus.publish(EventType.PLAN_CREATED, {"graph_id": graph.graph_id})

        # 2. Main Loop
        while not self.engine.is_finished:
            runnable = self.engine.get_runnable_nodes()
            
            if not runnable:
                if not self.engine.is_finished:
                    logger.warning("Deadlock or stalled graph detected.")
                break

            tasks = [self._execute_node(node) for node in runnable]
            await asyncio.gather(*tasks)

        return {"success": not self.engine.has_errors, "graph_id": graph.graph_id}

    async def _execute_node(self, node: Any) -> None:
        """Dispatches a node to the correct agent via the Event Bus."""
        self.engine.update_node(node.node_id, NodeStatus.RUNNING)
        await self.bus.publish(EventType.TASK_STARTED, {"node_id": node.node_id})
        
        # Simulate agent work
        await asyncio.sleep(0.1)
        
        # In a real system, an agent would listen to TASK_STARTED and publish TASK_COMPLETED
        # Here we simulate completion
        self.engine.update_node(node.node_id, NodeStatus.COMPLETED, output={"result": "success"})
        await self.bus.publish(EventType.TASK_COMPLETED, {"node_id": node.node_id})

if __name__ == "__main__":
    async def example():
        logging.basicConfig(level=logging.INFO)
        bus = EventBus()
        planner = HierarchicalPlanner(llm_client=None)
        orchestrator = Orchestrator(workspace="./tmp", planner=planner, bus=bus)
        
        async def log_event(p): print(f"LOG: {p}")
        bus.subscribe(EventType.TASK_COMPLETED, log_event)

        result = await orchestrator.run("Build a microservice for user auth")
        print(f"Final Result: {result}")

    asyncio.run(example())