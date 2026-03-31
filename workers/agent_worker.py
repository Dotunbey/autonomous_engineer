import asyncio
import logging
from typing import Any, Dict
from infra.queue import celery_app
from core.event_bus import EventBus
from core.planner import HierarchicalPlanner
from core.orchestrator import Orchestrator
from infra.persistence import GraphRepository

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, name="workers.agent_worker.execute_engineering_task")
def execute_engineering_task(self: Any, task_id: str, goal: str, workspace: str) -> Dict[str, Any]:
    """
    Executes an engineering task autonomously in the background via Celery.

    Args:
        self: The Celery task instance representing the current execution context.
        task_id: Unique identifier for the task.
        goal: The objective for the autonomous agent to accomplish.
        workspace: The directory path where the agent should operate.

    Returns:
        Dict[str, Any]: A dictionary containing the execution result and metadata.

    Raises:
        RuntimeError: If the orchestration loop encounters an unrecoverable failure.
    """
    logger.info(f"Worker picked up task {task_id}: {goal}")
    
    try:
        repository = GraphRepository()
        bus = EventBus()
        planner = HierarchicalPlanner(llm_client=None)
        
        orchestrator = Orchestrator(
            workspace=workspace,
            planner=planner,
            bus=bus
        )
        
        result = asyncio.run(orchestrator.run(goal))
        
        logger.info(f"Task {task_id} completed successfully.")
        return {
            "task_id": task_id,
            "status": "completed",
            "result": result
        }

    except Exception as exc:
        logger.error(f"Task {task_id} failed: {exc}")
        raise RuntimeError(f"Engineering execution failed: {exc}") from exc

if __name__ == "__main__":
    logger.info("To run this worker, execute the following in your terminal:")
    logger.info("celery -A infra.queue worker --loglevel=info")