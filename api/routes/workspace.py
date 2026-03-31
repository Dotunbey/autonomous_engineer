import os
import logging
from typing import Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from api.auth import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter()
WORKSPACE_DIR = "./workspace"

@router.get("/", response_model=Dict[str, List[str]], summary="List all files in the workspace")
async def list_workspace_files(api_key: str = Depends(verify_api_key)) -> Dict[str, List[str]]:
    """
    Scans the AI's workspace directory and returns a list of all generated files.
    """
    if not os.path.exists(WORKSPACE_DIR):
        return {"files": []}
        
    file_list = []
    for root, _, filenames in os.walk(WORKSPACE_DIR):
        for filename in filenames:
            # Get the relative path so it looks clean (e.g., "hello_world.py")
            rel_dir = os.path.relpath(root, WORKSPACE_DIR)
            if rel_dir == ".":
                file_list.append(filename)
            else:
                file_list.append(os.path.join(rel_dir, filename))
                
    return {"files": file_list}

@router.get("/{file_path:path}", summary="Read the contents of a specific file")
async def read_workspace_file(file_path: str, api_key: str = Depends(verify_api_key)) -> Dict[str, str]:
    """
    Reads and returns the exact code/text written by the AI agent.
    """
    full_path = os.path.join(WORKSPACE_DIR, file_path)
    
    # Security: Prevent directory traversal attacks (e.g., passing "../../etc/passwd")
    if not os.path.abspath(full_path).startswith(os.path.abspath(WORKSPACE_DIR)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied outside workspace bounds.")
        
    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"File '{file_path}' not found in workspace.")
        
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"filename": file_path, "content": content}
    except Exception as e:
        logger.error(f"Failed to read file {file_path}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not read file contents.")
