import asyncio
import logging
import uuid
from typing import Any, Dict

from core.planner import HierarchicalPlanner
from core.event_bus import EventBus
from infra.persistence import GraphRepository

logger = logging.getLogger(__name__)

class Orchestrator:
    """
    Manages the execution lifecycle: Planning -> Graph Building -> Agent Execution -> Completion.
    """
    def __init__(self, workspace: str, planner: HierarchicalPlanner, bus: EventBus):
        self.workspace = workspace
        self.planner = planner
        self.bus = bus
        self.repo = GraphRepository()
        self.graph_id = str(uuid.uuid4())

    async def _route_and_execute(self, role: str, description: str) -> Dict[str, Any]:
        """
        Dynamically initializes the correct agent based on the role and executes the task.
        """
        from tools.registry import ToolRegistry
        from memory.short_term import ShortTermMemory
        from memory.long_term import LongTermMemory
        from memory.retrieval import ContextRetriever
        from core.schema import TaskNode
        
        # 1. Initialize Memory & Tools for the Agent
        registry = ToolRegistry()
        
        # --- PRO FIX: Dynamic Tool Injection & Interception ---
        # Prevents 429 loops by ensuring the agent ALWAYS has access to file & shell tools.
        original_execute = getattr(registry, "execute", None)
        original_list_tools = getattr(registry, "list_tools", None)
        
        def safe_execute(action: str, **kwargs) -> str:
            # Intercept file writing tools
            if action in ["write_file", "create_file"]:
                path = kwargs.get("path", kwargs.get("filename", "output.txt"))
                content = kwargs.get("content", kwargs.get("code", ""))
                try:
                    import os
                    full_path = os.path.join(self.workspace, path)
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)
                    with open(full_path, "w") as f:
                        f.write(content)
                    return f"Success: Wrote to {path}"
                except Exception as e:
                    return f"Tool Execution Error: Failed to write file - {e}"
            
            # Intercept shell execution tools
            if action in ["run_shell_command", "execute_bash", "shell"]:
                cmd = kwargs.get("command", kwargs.get("cmd", ""))
                try:
                    import subprocess
                    res = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=self.workspace)
                    return f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
                except Exception as e:
                    return f"Tool Execution Error: Shell failure - {e}"
            
            # Fallback to standard registry tools if any
            if original_execute:
                try:
                    return original_execute(action, **kwargs)
                except Exception as e:
                    return f"Tool Execution Error: {str(e)}"
            return f"Tool Execution Error: Action '{action}' not recognized. Use 'write_file' or 'run_shell_command'."

        def safe_list_tools() -> list:
            tools = original_list_tools() if original_list_tools else []
            class InjectedTool:
                def __init__(self, name: str, desc: str):
                    self.name = name; self.description = desc
                def dict(self) -> dict:
                    return {"name": self.name, "description": self.description}
                    
            # Inject tools so they show up in the LLM's system prompt
            tools.append(InjectedTool("write_file", "Writes text to a file. Arguments: 'path' (string), 'content' (string)"))
            tools.append(InjectedTool("run_shell_command", "Executes a shell command. Arguments: 'command' (string)"))
            return tools

        # Bind the patched methods
        registry.execute = safe_execute
        registry.list_tools = safe_list_tools
        # ------------------------------------------------------

        retriever = ContextRetriever(ShortTermMemory(), LongTermMemory())
        
        # 2. Select the correct Specialized Agent
        AgentClass = None
        safe_role = role.lower().strip()
        
        try:
            if safe_role == "coder":
                from agents.coder import CoderAgent as AgentClass
            elif safe_role == "reviewer":
                from agents.reviewer import ReviewerAgent as AgentClass
            elif safe_role == "tester":
                from agents.tester import TesterAgent as AgentClass
            elif safe_role == "devops":
                from agents.devops import DevOpsAgent as AgentClass
            else:
                logger.warning(f"Unknown role '{role}'. Defaulting to CoderAgent.")
                from agents.coder import CoderAgent as AgentClass
        except ImportError as e:
            logger.error(f"Could not import agent for role {role}: {e}")
            from agents.coder import CoderAgent as AgentClass

        # 3. Instantiate the Agent (Pass the model_name to override defaults)
        agent = AgentClass(
            tool_registry=registry,
            retriever=retriever,
            llm_client=self.planner.llm_client,
            model_name=self.planner.model
        )
        
        # 4. Prepare Task Node and Context
        task = TaskNode(id=str(uuid.uuid4()), description=description, agent_role=role)
        context = {"workspace": self.workspace}
        
        # 5. Execute Task (Running synchronous agent loop in a thread to prevent blocking)
        result_task = await asyncio.to_thread(agent.execute_task, task, context)
        
        # Extract Enum value safely (if NodeStatus is an Enum)
        status_str = getattr(result_task.status, "name", str(result_task.status))
        
        return {
            "status": status_str,
            "output_data": result_task.output_data,
            "error_message": result_task.error_message
        }

    async def run(self, goal: str) -> Dict[str, Any]:
        """Main execution loop for the agent swarm."""
        logger.info("Initializing Orchestrator Run...")
        
        # 1. Ask the real LLM for a plan
        try:
            nodes = self.planner.create_plan(goal)
            # PRO FIX: Await the async event publisher to prevent Coroutine Warnings and graph tracking deadlocks
            await self.bus.publish("plan.created", {"nodes": len(nodes)})
        except Exception as e:
            logger.error("Planning phase failed.")
            return {"success": False, "error": str(e)}

        if not nodes:
            logger.warning("Planner returned an empty plan.")
            return {"success": False, "error": "Empty plan generated"}

        node_status = {n["id"]: "pending" for n in nodes}
        
        # 2. Naive Topological Execution Loop
        for node in nodes:
            node_id = node["id"]
            role = node["agent_role"]
            desc = node["description"]
            
            logger.info(f"Executing Node: [{node_id}] | Role: {role} | Desc: {desc}")
            await self.bus.publish("task.started", {"node_id": node_id})
            self.repo.update_node_status(node_id, "running")
            
            # --- ACTUAL AGENT WORK ---
            result = await self._route_and_execute(role, desc)
            
            # Extract final answer to check for masked API failures
            output_data = result.get("output_data") or {}
            final_answer = output_data.get("final_result", "") if isinstance(output_data, dict) else str(output_data)
            
            # 3. Deep Validation
            is_completed_status = result["status"] in ["COMPLETED", "NodeStatus.COMPLETED"]
            is_api_failure = "FAIL: System encountered an API error" in final_answer
            
            if is_completed_status and not is_api_failure:
                logger.info(f"Node {node_id} completed successfully by {role} agent.")
                node_status[node_id] = "completed"
                await self.bus.publish("task.completed", {"node_id": node_id, "status": "completed"})
                self.repo.update_node_status(node_id, "completed", output=result["output_data"])
            else:
                # Catch actual failures AND masked API failures
                error_msg = final_answer if is_api_failure else result.get("error_message", "Unknown error")
                logger.error(f"Node {node_id} failed: {error_msg}")
                node_status[node_id] = "failed"
                await self.bus.publish("task.failed", {"node_id": node_id, "error": error_msg})
                self.repo.update_node_status(node_id, "failed", error=error_msg)
                
                # Halt execution on failure
                return {
                    "success": False, 
                    "graph_id": self.graph_id,
                    "executed_nodes": node_status,
                    "error": f"Execution halted at node {node_id}: {error_msg}"
                }

        logger.info("All nodes completed successfully.")
        
        return {
            "success": True, 
            "graph_id": self.graph_id,
            "executed_nodes": node_status
        }