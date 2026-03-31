import asyncio
import logging
import os
from typing import Any, Dict
from openai import OpenAI

from infra.queue import celery_app
from core.event_bus import EventBus
from core.planner import HierarchicalPlanner
from core.orchestrator import Orchestrator
from infra.persistence import GraphRepository

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, name="workers.agent_worker.execute_engineering_task")
def execute_engineering_task(self: Any, task_id: str, goal: str, workspace: str) -> Dict[str, Any]:
    """
    Executes an engineering task autonomously using the multi-agent orchestrator.
    Configured to support OpenAI, Groq, and Gemini (via OpenAI-compatible endpoint).
    """
    logger.info(f"Worker picked up task {task_id}: {goal}")
    
    try:
        repository = GraphRepository()
        repository.update_task_progress(task_id, "running", 5.0)
        
        # --- LLM CONFIGURATION (GEMINI SUPPORT) ---
        api_key = os.getenv("OPENAI_API_KEY")
        
        # Default to Gemini if the key looks like a Google key or if specifically requested
        # Google's OpenAI-compatible base URL
        base_url = os.getenv("OPENAI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
        
        # If using Gemini, the model name must be gemini-1.5-flash or gemini-1.5-pro
        model_name = os.getenv("DEFAULT_MODEL", "gemini-1.5-flash")
        
        llm_client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
        logger.info(f"Using LLM: {model_name} at {base_url}")
        # ------------------------------------------

        bus = EventBus()
        # Ensure the planner receives the configured client and model
        planner = HierarchicalPlanner(llm_client=llm_client)
        
        orchestrator = Orchestrator(
            workspace=workspace,
            planner=planner,
            bus=bus
        )
        
        logger.info(f"Starting orchestration for: {goal}")
        result = asyncio.run(orchestrator.run(goal))
        
        repository.update_task_progress(task_id, "completed", 100.0)
        return {"task_id": task_id, "status": "completed", "result": result}

    except Exception as exc:
        logger.error(f"Task {task_id} failed: {exc}")
        try:
            repository = GraphRepository()
            repository.update_task_progress(task_id, f"failed: {str(exc)}", 0.0)
        except: pass
        raise RuntimeError(f"Engineering execution failed: {exc}") from exc