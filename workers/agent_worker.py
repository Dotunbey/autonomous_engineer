
#!workers/agent_worker.py
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
    Executes an engineering task autonomously.
    """
    logger.info(f"Worker picked up task {task_id}: {goal}")
    
    try:
        repository = GraphRepository()
        # Initialize status in DB
        repository.update_task_progress(task_id, "running", 10.0)
        
        bus = EventBus()
        planner = HierarchicalPlanner(llm_client=None)
        
        orchestrator = Orchestrator(
            workspace=workspace,
            planner=planner,
            bus=bus
        )
        
        result = asyncio.run(orchestrator.run(goal))
        
        repository.update_task_progress(task_id, "completed", 100.0)
        logger.info(f"Task {task_id} completed successfully.")
        return {
            "task_id": task_id,
            "status": "completed",
            "result": result
        }

    except Exception as exc:
        logger.error(f"Task {task_id} failed: {exc}")
        # Ensure failure is persisted
        try:
            repository = GraphRepository()
            repository.update_task_progress(task_id, f"failed: {str(exc)}", 0.0)
        except:
            pass
        raise RuntimeError(f"Engineering execution failed: {exc}") from exc