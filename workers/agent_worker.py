#!workers/agent_worker.py
import asyncio
import logging
from typing import Any, Dict
from infra.queue import celery_app
from infra.persistence import GraphRepository

# Note: We import the orchestrator here. 
# Ensure core/orchestrator.py exists and has a run method.
from core.orchestrator import Orchestrator 
from core.planner import HierarchicalPlanner
from core.event_bus import EventBus

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, name="workers.agent_worker.execute_engineering_task")
def execute_engineering_task(self: Any, task_id: str, goal: str, workspace: str) -> Dict[str, Any]:
    logger.info(f"Worker picked up task {task_id}: {goal}")
    
    repo = GraphRepository()
    # Update status to 'running' so the UI sees it
    repo.update_task_progress(task_id, "running", 10.0)
    
    try:
        bus = EventBus()
        planner = HierarchicalPlanner(llm_client=None)
        orchestrator = Orchestrator(workspace=workspace, planner=planner, bus=bus)
        
        # Real execution
        result = asyncio.run(orchestrator.run(goal))
        
        repo.update_task_progress(task_id, "completed", 100.0)
        return {"task_id": task_id, "status": "completed", "result": result}

    except Exception as exc:
        logger.error(f"Task {task_id} failed: {exc}")
        repo.update_task_progress(task_id, f"failed: {str(exc)}", 0.0)
        raise RuntimeError(f"Engineering execution failed: {exc}") from exc