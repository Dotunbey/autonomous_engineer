import json
import logging
from typing import Any, Dict, Optional
from agents.base_agent import BaseAgent
from core.schema import TaskNode
from tools.registry import ToolRegistry
from memory.retrieval import ContextRetriever

logger = logging.getLogger(__name__)

class CoderAgent(BaseAgent):
    """
    Specialized agent responsible for writing, modifying, and executing code.
    Utilizes tools and memory to iteratively satisfy engineering tasks.
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        retriever: ContextRetriever,
        llm_client: Any,
        model_name: str = "llama3-70b-8192"
    ):
        """
        Initializes the CoderAgent.

        Args:
            tool_registry: The system tool registry.
            retriever: The RAG engine for memory context.
            llm_client: An OpenAI-compatible client instance.
            model_name: The specific model string to invoke.
        """
        super().__init__(role="coder", tool_registry=tool_registry, llm_client=llm_client)
        self._retriever = retriever
        self._model_name = model_name

    @property
    def system_prompt(self) -> str:
        """Defines the core persona, capabilities, and strict JSON output rules."""
        return f"""You are an Autonomous Software Engineer.
Your goal is to write, execute, and debug code to complete the user's task.
You have access to the following tools:
{self._format_available_tools()}

You MUST respond in strict JSON format. Do not include markdown formatting or conversational text outside the JSON object.
Expected JSON format when taking an action:
{{
    "thought": "Explanation of what I need to do next",
    "action": "tool_name",
    "action_input": {{"param1": "value1"}},
    "is_complete": false
}}

Expected JSON format when the task is fully completed:
{{
    "thought": "Explanation of how the task was accomplished",
    "is_complete": true,
    "answer": "Summary of the final outcome and files modified"
}}
"""

    def _think(self, task_desc: str, last_observation: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invokes the LLM to determine the next action in the ReAct loop.

        Args:
            task_desc: The current task objective.
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

What is your next action? Output ONLY valid JSON.
"""
        
        try:
            response = self._llm.chat.completions.create(
                model=self._model_name,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=1000
            )
            raw_content = response.choices[0].message.content.strip()
            return self._parse_json_response(raw_content)
        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            return {
                "thought": "I encountered an API error.",
                "action": "terminal",
                "action_input": {"command": "echo 'LLM Error Recovering'"},
                "is_complete": False
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
    
    # Example using a free local Ollama instance or Groq
    mock_client = OpenAI(
        base_url=os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1"),
        api_key=os.getenv("OPENAI_API_KEY", "mock-key")
    )
    
    registry = ToolRegistry()
    retriever = ContextRetriever(ShortTermMemory(), LongTermMemory())
    
    coder = CoderAgent(registry, retriever, mock_client, model_name="qwen2.5-coder:7b")
    print(coder.system_prompt)