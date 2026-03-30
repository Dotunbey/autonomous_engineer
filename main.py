import asyncio
from core.schema import WorkflowGraph, TaskNode, NodeStatus, EventType
from core.event_bus import EventBus
from core.execution_graph import ExecutionGraphEngine

async def on_task_completed(payload: dict):
    print(f"EVENT RECEIVED: Task {payload['node_id']} finished with status: {payload['status']}")

async def main():
    # 1. Setup Infrastructure
    bus = EventBus()
    bus.subscribe(EventType.TASK_COMPLETED, on_task_completed)

    # 2. Define a simple DAG: A -> B
    node_a = TaskNode(node_id="A", description="Write Code", agent_role="coder")
    node_b = TaskNode(node_id="B", description="Run Tests", agent_role="tester", dependencies={"A"})
    
    graph = WorkflowGraph(graph_id="W-001", nodes={"A": node_a, "B": node_b})
    engine = ExecutionGraphEngine(graph)

    # 3. Simulate Execution Loop
    while not engine.is_workflow_complete:
        runnable = engine.get_ready_nodes()
        
        for node in runnable:
            print(f"Executing: {node.description}")
            # Simulate tool work
            engine.update_node_status(node.node_id, NodeStatus.RUNNING)
            await asyncio.sleep(0.5)
            engine.update_node_status(node.node_id, NodeStatus.COMPLETED)
            
            # Publish event
            await bus.publish(EventType.TASK_COMPLETED, {"node_id": node.node_id, "status": "COMPLETED"})

    print(f"Workflow finished. Total progress: {engine.progress_percentage}%")

if __name__ == "__main__":
    asyncio.run(main())