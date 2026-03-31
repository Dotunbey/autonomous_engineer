#!autonomous_engineer/agents/planner_agent.py
import json
import logging
from typing import Any, Dict

from autonomous_engineer.agents.base_agent import BaseAgent
from autonomous_engineer.memory.retrieval import ContextRetriever
from autonomous_engineer.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class PlannerAgent(BaseAgent):
    """
    Specialized agent responsible for exploring the repository and
    breaking down high-level goals into a Directed Acyclic Graph (DAG) of tasks.
    Replaces the monolithic core/planner.py with a ReAct-capable agent.
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        retriever: ContextRetriever,
        llm_client: Any,
        model_name: str = "llama3-70b-8192",
    ) -> None:
        """
        Initializes the PlannerAgent.

        Args:
            tool_registry: Registry of available tools for codebase exploration.
            retriever: RAG engine for memory context.
            llm_client: OpenAI-compatible client instance.
            model_name: The specific model string to invoke.
        """
        super().__init__(role="planner", tool_registry=tool_registry, llm_client=llm_client)
        self._retriever = retriever
        self._model_name = model_name

    @property
    def system_prompt(self) -> str:
        """
        Defines the planner persona and enforces the structured DAG output schema.
        
        Returns:
            str: The formatted system prompt.
        """
        return f"""You are the Lead Architectural Planner Agent.
Your goal is to understand the user's objective, explore the codebase if necessary, and break the objective down into a precise execution plan (a Directed Acyclic Graph of tasks).
You have access to the following tools:
{self._format_available_tools()}

You MUST respond in strict JSON format.

Expected JSON format when gathering context (e.g., listing files, grepping):
{{
    "thought": "Explanation of what context I need to gather.",
    "action": "tool_name",
    "action_input": {{"param1": "value1"}},
    "is_complete": false
}}

Expected JSON format when the plan is finalized:
{{
    "thought": "I have enough context. Here is the final execution DAG.",
    "is_complete": true,
    "answer": {{
        "nodes": [
            {{"id": "task_1", "description": "Setup DB", "agent_role": "coder"}},
            {{"id": "task_2", "description": "Write API", "agent_role": "coder"}},
            {{"id": "task_3", "description": "Test API", "agent_role": "tester"}}
        ],
        "dependencies": [
            {{"from": "task_1", "to": "task_2"}},
            {{"from": "task_2", "to": "task_3"}}
        ]
    }}
}}
"""

    def _think(self, task_desc: str, last_observation: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invokes the LLM to determine the next context-gathering step or finalize the plan.

        Args:
            task_desc: The high-level objective to plan for.
            last_observation: Output from the previous tool execution.
            context: Environment state variables.

        Returns:
            Dict[str, Any]: The parsed JSON response containing the next action or final plan.
        """
        retrieved_context = self._retriever.build_agent_context(task_desc, context)

        prompt = f"""
{retrieved_context}

LAST OBSERVATION:
{str(last_observation)}

What is your next action? Output ONLY valid JSON.
"""

        try:
            response = self._llm.chat.completions.create(
                model=self._model_name,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=1500,
            )
            raw_content = response.choices[0].message.content.strip()
            return self._parse_json_response(raw_content)
        except Exception as e:
            logger.error(f"PlannerAgent LLM API call failed: {e}")
            return {
                "thought": f"API error encountered: {e}",
                "is_complete": True,
                "answer": {"error": "Failed to generate plan due to API error."}
            }

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """
        Safely extracts and parses JSON from the raw LLM output.

        Args:
            text: The raw text response.

        Returns:
            Dict[str, Any]: The parsed dictionary.
        """
        clean_text = text.replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(clean_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON: {e} | Content: {clean_text}")
            return {
                "thought": "My previous output was invalid JSON. I must fix my formatting.",
                "is_complete": False,
            }