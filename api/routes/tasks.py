#!api/routes/tasks.py
import logging
import uuid
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.auth import verify_api_key
from infra.persistence import GraphRepository
from workers.agent_worker import execute_engineering_task

logger = logging.getLogger(__name__)

router = APIRouter()
repo = GraphRepository()

class TaskRequest(BaseModel):
    """Schema for incoming engineering task requests."""
    goal: str = Field(..., description="The high-level objective for the agent.")
    workspace_dir: Optional[str] = Field(default="./workspace", description="Target directory for the project.")

class TaskResponse(BaseModel):
    """Schema for task creation responses."""
    task_id: str
    status: str
    message: str

@router.post("/", response_model=TaskResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_task(
    request: TaskRequest,
    api_key: str = Depends(verify_api_key)
) -> TaskResponse:
    """
    Submits a new engineering goal to the autonomous system.
    Saves to SQLite and triggers the Celery worker via Redis.
    """
    task_id = f"task_{uuid.uuid4().hex[:12]}"
    
    # 1. Persist the task so the UI can find it
    try:
        repo.save_task(task_id, request.goal, request.workspace_dir)
        
        # 2. Trigger the Celery Worker (asynchronous)
        # This sends the task to your Upstash Redis queue
        execute_engineering_task.delay(task_id, request.goal, request.workspace_dir)
        
        return TaskResponse(
            task_id=task_id,
            status="accepted",
            message="Task has been queued and persistence initialized."
        )
    except Exception as e:
        logger.error(f"Failed to initialize task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal persistence or queue error.")

@router.get("/{task_id}", response_model=Dict[str, Any])
async def get_task_status(task_id: str, api_key: str = Depends(verify_api_key)) -> Dict[str, Any]:
    """
    Retrieves the current status of a task from the SQLite database.
    """
    state = repo.load_task_state(task_id)
    if not state:
        raise HTTPException(status_code=404, detail="Task not found in database.")

    return state