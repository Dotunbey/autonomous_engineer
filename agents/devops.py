#!autonomous_engineer/agents/devops.py
import json
import logging
from typing import Any, Dict

from autonomous_engineer.agents.base_agent import BaseAgent
from autonomous_engineer.memory.retrieval import ContextRetriever
from autonomous_engineer.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class DevOpsAgent(BaseAgent):
    """
    Specialized agent responsible for containerization, deployment scripts,
    and managing CI/CD pipelines.
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        retriever: ContextRetriever,
        llm_client: Any,
        model_name: str = "llama3-70b-8192",
    ) -> None:
        """
        Initializes the DevOpsAgent.

        Args:
            tool_registry: Registry of available tools (e.g., docker, github).
            retriever: RAG engine for memory context.
            llm_client: OpenAI-compatible client instance.
            model_name: The specific model string to invoke.
        """
        super().__init__(role="devops", tool_registry=tool_registry, llm_client=llm_client)
        self._retriever = retriever
        self._model_name = model_name

    @property
    def system_prompt(self) -> str:
        """
        Defines the DevOps persona focusing on infrastructure and delivery.
        
        Returns:
            str: The formatted system prompt.
        """
        return f"""You are the Senior Site Reliability and DevOps Engineer.
Your goal is to configure infrastructure (Dockerfiles, docker-compose), write CI/CD pipelines (.github/workflows), and ensure smooth deployments.
You have access to the following tools:
{self._format_available_tools()}

You MUST respond in strict JSON format.

Expected JSON format for taking an action (e.g., writing a Dockerfile):
{{
    "thought": "I need to write a Dockerfile for the FastAPI service.",
    "action": "write_file",
    "action_input": {{"path": "Dockerfile", "content": "FROM python:3.9-slim\\n..."}},
    "is_complete": false
}}

Expected JSON format when devops tasks are complete:
{{
    "thought": "Docker configuration and CI/CD pipelines are fully setup.",
    "is_complete": true,
    "answer": "Infrastructure configured successfully."
}}
"""

    def _think(self, task_desc: str, last_observation: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invokes the LLM to execute infrastructure tasks.

        Args:
            task_desc: The current devops objective.
            last_observation: Output from the previous tool execution.
            context: Environment state variables.

        Returns:
            Dict[str, Any]: The parsed JSON response.
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
                max_tokens=1200,
            )
            raw_content = response.choices[0].message.content.strip()
            return self._parse_json_response(raw_content)
        except Exception as e:
            logger.error(f"DevOpsAgent LLM API call failed: {e}")
            return {
                "thought": f"API error encountered: {e}",
                "is_complete": True,
                "answer": "FAIL: System encountered an API error during devops configuration."
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