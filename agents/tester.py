#!autonomous_engineer/agents/tester.py
import json
import logging
from typing import Any, Dict

from autonomous_engineer.agents.base_agent import BaseAgent
from autonomous_engineer.memory.retrieval import ContextRetriever
from autonomous_engineer.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class TesterAgent(BaseAgent):
    """
    Specialized agent dedicated to writing, running, and analyzing unit/integration tests.
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        retriever: ContextRetriever,
        llm_client: Any,
        model_name: str = "llama3-70b-8192",
    ) -> None:
        """
        Initializes the TesterAgent.

        Args:
            tool_registry: Registry of available tools.
            retriever: RAG engine for memory context.
            llm_client: OpenAI-compatible client instance.
            model_name: The specific model string to invoke.
        """
        super().__init__(role="tester", tool_registry=tool_registry, llm_client=llm_client)
        self._retriever = retriever
        self._model_name = model_name

    @property
    def system_prompt(self) -> str:
        """
        Defines the tester persona and enforces strict test execution protocols.
        
        Returns:
            str: The formatted system prompt.
        """
        return f"""You are the Lead QA Automation Engineer.
Your goal is to write robust test cases, execute them using the terminal, and report on the coverage and pass/fail states.
You have access to the following tools:
{self._format_available_tools()}

You MUST respond in strict JSON format.

Expected JSON format for taking an action (e.g., writing a test file or running pytest):
{{
    "thought": "I need to execute the test suite to verify the coder's changes.",
    "action": "run_shell_command",
    "action_input": {{"command": "pytest tests/ --tb=short"}},
    "is_complete": false
}}

Expected JSON format when testing is complete:
{{
    "thought": "Tests executed successfully. Coverage is adequate.",
    "is_complete": true,
    "answer": "All tests passed. Logs attached."
}}
"""

    def _think(self, task_desc: str, last_observation: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invokes the LLM to write tests or evaluate terminal output.

        Args:
            task_desc: The current testing objective.
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
                temperature=0.1,  # Lower temperature for deterministic test parsing
                max_tokens=1000,
            )
            raw_content = response.choices[0].message.content.strip()
            return self._parse_json_response(raw_content)
        except Exception as e:
            logger.error(f"TesterAgent LLM API call failed: {e}")
            return {
                "thought": f"API error encountered: {e}",
                "is_complete": True,
                "answer": "FAIL: System encountered an API error during testing."
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