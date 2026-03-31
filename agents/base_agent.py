import logging
import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from core.schema import TaskNode, NodeStatus
from tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """
    Abstract Base Class for all specialized AI agents (Coder, Reviewer, etc.).
    Implements a ReAct (Reason -> Act -> Observe) loop.
    """

    def __init__(self, role: str, tool_registry: ToolRegistry, llm_client: Any = None):
        """
        Args:
            role: The specific persona/role of this agent (e.g., 'coder').
            tool_registry: Access to the system's registered tools.
            llm_client: The mock or real LLM client for generating responses.
        """
        self.role = role
        self.tools = tool_registry
        self._llm = llm_client
        self.max_iterations = 10

    @abstractmethod
    def system_prompt(self) -> str:
        """Defines the agent's persona, rules, and constraints."""
        pass

    def _format_available_tools(self) -> str:
        """Returns a formatted string of tools the agent can use."""
        tool_list = self.tools.list_tools()
        return json.dumps([t.dict() for t in tool_list], indent=2)

    def execute_task(self, task: TaskNode, context: Dict[str, Any]) -> TaskNode:
        """
        Runs the autonomous reasoning and execution loop for a specific task.

        Args:
            task: The TaskNode containing the description of work.
            context: Project state and environment variables.

        Returns:
            The updated TaskNode (Status: COMPLETED or FAILED).
        """
        logger.info(f"[{self.role}] Starting task: {task.description}")
        
        iteration = 0
        observation = "Task started."
        
        while iteration < self.max_iterations:
            iteration += 1
            logger.debug(f"[{self.role}] Iteration {iteration}")
            
            # 1. Reason (Ask LLM what to do next based on observation)
            thought_process = self._think(task.description, observation, context)
            
            # 2. Check for completion
            if thought_process.get("is_complete"):
                logger.info(f"[{self.role}] Task completed successfully.")
                task.status = NodeStatus.COMPLETED
                task.output_data = {"final_result": thought_process.get("answer")}
                return task
                
            # 3. Act (Execute the chosen tool)
            action = thought_process.get("action")
            action_input = thought_process.get("action_input", {})
            
            if action:
                try:
                    observation = self.tools.execute(action, **action_input)
                except Exception as e:
                    observation = f"Tool Execution Error: {str(e)}"
                    logger.warning(f"[{self.role}] Tool error: {observation}")
            else:
                observation = "Error: No action provided by the reasoning engine."

        # If loop exhausts without completion
        logger.error(f"[{self.role}] Task failed: Max iterations reached.")
        task.status = NodeStatus.FAILED
        task.error_message = "Max reasoning iterations reached without completion."
        return task

    def _think(self, task_desc: str, last_observation: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulates the LLM call. In production, this formats the prompt and calls OpenAI/Anthropic.
        Expects a structured JSON response containing 'action', 'action_input', or 'is_complete'.
        """
        # MOCK IMPLEMENTATION: Simulating an agent deciding to use a tool, then finishing.
        if "Task started" in str(last_observation):
            return {
                "thought": "I need to check the files in the directory to understand the project.",
                "action": "list_files",
                "action_input": {"directory": "."},
                "is_complete": False
            }
        else:
            return {
                "thought": "I have the information I need.",
                "is_complete": True,
                "answer": "Analyzed directory structure."
            }