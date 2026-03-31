import os
import json
import logging
import uuid
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

class HierarchicalPlanner:
    """
    Connects to the LLM (Gemini/OpenAI) to break down a high-level goal
    into a directed acyclic graph (DAG) of executable nodes.
    """
    def __init__(self, llm_client: Any):
        self.llm_client = llm_client
        self.model = os.getenv("DEFAULT_MODEL", "gemini-1.5-flash")

    def create_plan(self, goal: str) -> List[Dict[str, Any]]:
        """Calls the LLM to generate a task plan."""
        logger.info(f"Generating real plan for goal: {goal}")
        
        system_prompt = """
        You are an expert AI software architect. Break down the user's engineering goal into a step-by-step execution plan.
        You MUST respond ONLY with a valid JSON object. Do NOT wrap it in markdown blockquotes (e.g. ```json).
        
        The JSON must match this structure exactly:
        {
            "nodes": [
                {
                    "id": "step_1",
                    "description": "Create the hello_world.py file and write the print statement.",
                    "agent_role": "coder",
                    "dependencies": []
                },
                {
                    "id": "step_2",
                    "description": "Review the file to ensure it prints exactly 'Hello from Render'.",
                    "agent_role": "reviewer",
                    "dependencies": ["step_1"]
                }
            ]
        }
        Keep the plan concise (1 to 3 steps maximum for simple tasks).
        """

        try:
            response = self.llm_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": goal}
                ],
                temperature=0.2
            )
            
            raw_content = response.choices[0].message.content.strip()
            
            # Clean up potential markdown formatting from the LLM
            if raw_content.startswith("```json"):
                raw_content = raw_content[7:-3].strip()
            elif raw_content.startswith("```"):
                raw_content = raw_content[3:-3].strip()
                
            plan_data = json.loads(raw_content)
            
            # Sanitize and ensure IDs are standard
            nodes = plan_data.get("nodes", [])
            for node in nodes:
                # Guarantee required fields
                node.setdefault("id", f"node_{uuid.uuid4().hex[:8]}")
                node.setdefault("agent_role", "coder")
                node.setdefault("dependencies", [])
                
            logger.info(f"Successfully generated {len(nodes)} nodes from LLM.")
            return nodes

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {raw_content}")
            raise RuntimeError("Planner received invalid JSON from LLM") from e
        except Exception as e:
            logger.error(f"LLM API call failed: {e}")