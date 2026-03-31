#!infra/persistence.py
import json
import sqlite3
import logging
import os
from typing import Any, Dict, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

class GraphRepository:
    """
    Handles persistence for the Autonomous Execution Graph (DAG).
    Ensures that agent progress is saved to SQLite to survive crashes or restarts.
    """

    def __init__(self, db_path: str = "data/agent_data.db"):
        """
        Initializes the repository and creates necessary tables if they don't exist.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = db_path
        self._ensure_data_dir()
        self._init_db()

    def _ensure_data_dir(self) -> None:
        """Creates the data directory if it doesn't exist."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def _init_db(self) -> None:
        """Sets up the database schema for tasks and execution state."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Table for high-level tasks
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    goal TEXT NOT NULL,
                    workspace TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    progress REAL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Table for individual graph nodes (DAG steps)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS graph_nodes (
                    node_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    description TEXT NOT NULL,
                    agent_role TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    output_data TEXT,
                    error_message TEXT,
                    FOREIGN KEY (task_id) REFERENCES tasks (id)
                )
            """)
            conn.commit()

    def save_task(self, task_id: str, goal: str, workspace: str) -> None:
        """Creates a new task record."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO tasks (id, goal, workspace) VALUES (?, ?, ?)",
                (task_id, goal, workspace)
            )
            conn.commit()

    def update_task_progress(self, task_id: str, status: str, progress: float) -> None:
        """Updates the overall status and percentage of a task."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE tasks SET status = ?, progress = ?, updated_at = ? WHERE id = ?",
                (status, progress, datetime.now().isoformat(), task_id)
            )
            conn.commit()

    def save_nodes(self, task_id: str, nodes: List[Dict[str, Any]]) -> None:
        """Stores the generated DAG nodes for a task."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for node in nodes:
                cursor.execute("""
                    INSERT OR REPLACE INTO graph_nodes 
                    (node_id, task_id, description, agent_role, status) 
                    VALUES (?, ?, ?, ?, ?)
                """, (node['id'], task_id, node['description'], node['agent_role'], 'pending'))
            conn.commit()

    def update_node_status(self, node_id: str, status: str, output: Optional[Dict] = None, error: Optional[str] = None) -> None:
        """Updates the state of a specific node in the execution graph."""
        output_json = json.dumps(output) if output else None
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE graph_nodes 
                SET status = ?, output_data = ?, error_message = ? 
                WHERE node_id = ?
            """, (status, output_json, error, node_id))
            conn.commit()

    def load_task_state(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves the full state of a task and its nodes for the UI or Orchestrator."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get main task info
            task = cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            if not task:
                return None
                
            # Get associated nodes
            nodes = cursor.execute("SELECT * FROM graph_nodes WHERE task_id = ?", (task_id,)).fetchall()
            
            return {
                "task_id": task["id"],
                "goal": task["goal"],
                "status": task["status"],
                "progress_percentage": task["progress"],
                "active_nodes": [n["description"] for n in nodes if n["status"] == "running"],
                "all_nodes": [dict(n) for n in nodes]
            }

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    repo = GraphRepository(db_path="data/test_persistence.db")
    
    # Example: Simulating a task start
    tid = "task_001"
    repo.save_task(tid, "Fix the auth module", "./workspace/auth")
    repo.save_nodes(tid, [
        {"id": "node_1", "description": "Gather requirements", "agent_role": "planner"},
        {"id": "node_2", "description": "Write JWT code", "agent_role": "coder"}
    ])
    
    # Simulating progress
    repo.update_node_status("node_1", "completed", output={"files_found": ["main.py"]})
    repo.update_task_progress(tid, "running", 50.0)
    
    state = repo.load_task_state(tid)
    print(f"Current State: {state}")