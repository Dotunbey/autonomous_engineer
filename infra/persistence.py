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
        self.db_path = db_path
        self._ensure_data_dir()
        self._init_db()

    def _ensure_data_dir(self) -> None:
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
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
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO tasks (id, goal, workspace, status, progress) VALUES (?, ?, ?, 'pending', 0.0)",
                (task_id, goal, workspace)
            )
            conn.commit()

    def update_task_progress(self, task_id: str, status: str, progress: float) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE tasks SET status = ?, progress = ?, updated_at = ? WHERE id = ?",
                (status, progress, datetime.now().isoformat(), task_id)
            )
            conn.commit()

    def save_nodes(self, task_id: str, nodes: List[Dict[str, Any]]) -> None:
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
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            task = cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            if not task:
                return None
            nodes = cursor.execute("SELECT * FROM graph_nodes WHERE task_id = ?", (task_id,)).fetchall()
            return {
                "task_id": task["id"],
                "goal": task["goal"],
                "status": task["status"],
                "progress_percentage": task["progress"],
                "active_nodes": [n["description"] for n in nodes if n["status"] == "running"],
                "all_nodes": [dict(n) for n in nodes]
            }