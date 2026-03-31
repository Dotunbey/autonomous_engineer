#!memory/retrieval.py
import logging
from typing import Any, Dict, List
from memory.short_term import ShortTermMemory
from memory.long_term import LongTermMemory

logger = logging.getLogger(__name__)

class ContextRetriever:
    """
    The RAG (Retrieval-Augmented Generation) engine.
    Orchestrates Short Term, Long Term, and Tool-based Codebase context
    into a single optimized prompt block for the LLM.
    """

    def __init__(self, short_term: ShortTermMemory, long_term: LongTermMemory):
        """
        Args:
            short_term: The sliding window memory instance.
            long_term: The persistent vector memory instance.
        """
        self._stm = short_term
        self._ltm = long_term

    def build_agent_context(self, current_task: str, environment_data: Dict[str, Any]) -> str:
        """
        Constructs a highly relevant context string for the Agent's reasoning loop.

        Args:
            current_task: What the agent is trying to accomplish right now.
            environment_data: Data such as current active files, OS info, etc.

        Returns:
            A formatted string containing historical lessons and recent actions.
        """
        logger.info("Building retrieved context for agent prompt.")
        
        # 1. Fetch relevant historical knowledge (Long Term)
        historical_records = self._ltm.search(current_task, top_k=2)
        history_context = "\n".join([f"- {r.content}" for r in historical_records])
        if not history_context:
            history_context = "No relevant historical playbooks found."

        # 2. Fetch immediate past actions (Short Term)
        recent_logs = self._stm.get_recent_context(limit=5)
        recent_context = "\n".join(
            [f"[{log['action_type']}] Success={log['success']}: {log['details']}" for log in recent_logs]
        )
        if not recent_context:
            recent_context = "No recent actions in this session."

        # 3. Format Environment Data
        env_context = "\n".join([f"{k}: {v}" for k, v in environment_data.items()])

        # 4. Assemble Final Context Block
        assembled_context = f"""
=== SYSTEM CONTEXT ===
{env_context}

=== RELEVANT PLAYBOOKS & PAST FIXES ===
{history_context}

=== RECENT ACTIONS LOG ===
{recent_context}

=== CURRENT OBJECTIVE ===
{current_task}
"""
        return assembled_context.strip()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Setup mock memories
    stm = ShortTermMemory()
    ltm = LongTermMemory("data/mock_db.json")
    ltm.add_memory("fix-101", "If tests fail with 'ModuleNotFoundError', check the PYTHONPATH.", {"type": "bugfix"})
    stm.add_event("TEST_EXEC", "pytest failed with ModuleNotFoundError", False)
    
    retriever = ContextRetriever(short_term=stm, long_term=ltm)
    
    context_prompt = retriever.build_agent_context(
        current_task="Fix the broken CI pipeline locally.",
        environment_data={"OS": "Linux", "Python": "3.9", "Active_File": "tests/test_api.py"}
    )
    
    print("\n" + context_prompt)