import json
import logging
from typing import Any, Dict
from agents.base_agent import BaseAgent
from core.schema import TaskNode
from tools.registry import ToolRegistry
from memory.retrieval import ContextRetriever

logger = logging.getLogger(__name__)

class ReviewerAgent(BaseAgent):
    """
    Specialized QA agent responsible for auditing code, running tests,
    and enforcing system architectural standards.
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        retriever: ContextRetriever,
        llm_client: Any,
        model_name: str = "llama3-70b-8192"
    ):
        """
        Initializes the ReviewerAgent.

        Args:
            tool_registry: The system tool registry.
            retriever: The RAG engine for memory context.
            llm_client: An OpenAI-compatible client instance.
            model_name: The specific model string to invoke.
        """
        super().__init__(role="reviewer", tool_registry=tool_registry, llm_client=llm_client)
        self._retriever = retriever
        self._model_name = model_name

    @property
    def system_prompt(self) -> str:
        """Defines the core persona, capabilities, and strict JSON output rules."""
        return f"""You are an Expert Code Reviewer and QA Engineer.
Your goal is to verify that the code written by the CoderAgent satisfies the task, passes static analysis, and contains no security vulnerabilities.
You have access to the following tools:
{self._format_available_tools()}

You MUST respond in strict JSON format.
Expected JSON format when taking an action (like running tests or checking files):
{{
    "thought": "Explanation of what I am testing next",
    "action": "tool_name",
    "action_input": {{"param1": "value1"}},
    "is_complete": false
}}

Expected JSON format when the review is finalized:
{{
    "thought": "Final assessment of the code quality.",
    "is_complete": true,
    "answer": "PASS or FAIL. If FAIL, provide specific reasons and required fixes."
}}
"""

    def _think(self, task_desc: str, last_observation: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invokes the LLM to determine the next testing/review action.

        Args:
            task_desc: The review objective.
            last_observation: The output from the previous tool execution.
            context: Environment state dict.

        Returns:
            A dictionary containing the parsed LLM JSON response.
        """
        retrieved_context = self._retriever.build_agent_context(task_desc, context)
        
        prompt = f"""
{retrieved_context}

LAST OBSERVATION:
{str(last_observation)}

What is your next action to verify the code? Output ONLY valid JSON.
"""
        
        try:
            response = self._llm.chat.completions.create(
                model=self._model_name,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )
            raw_content = response.choices[0].message.content.strip()
            return self._parse_json_response(raw_content)
        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            return {
                "thought": "I encountered an API error.",
                "is_complete": True,
                "answer": "FAIL: System encountered an API error during review."
            }

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """
        Safely extracts and parses JSON from the LLM output.

        Args:
            text: The raw text response from the LLM.

        Returns:
            A parsed dictionary.
        """
        clean_text = text.replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(clean_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON: {e} | Content: {clean_text}")
            return {
                "thought": "My previous output was invalid JSON. I must fix my formatting.",
                "is_complete": False
            }

if __name__ == "__main__":
    from tools.registry import ToolRegistry
    from memory.short_term import ShortTermMemory
    from memory.long_term import LongTermMemory
    from memory.retrieval import ContextRetriever
    from openai import OpenAI
    import os

    logging.basicConfig(level=logging.INFO)
    
    mock_client = OpenAI(
        base_url=os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1"),
        api_key=os.getenv("OPENAI_API_KEY", "mock-key")
    )
    
    registry = ToolRegistry()
    retriever = ContextRetriever(ShortTermMemory(), LongTermMemory())
    
    reviewer = ReviewerAgent(registry, retriever, mock_client, model_name="qwen2.5-coder:7b")
    print(reviewer.system_prompt)