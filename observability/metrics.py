import logging
from typing import Dict

from prometheus_client import Counter, Histogram, start_http_server

logger = logging.getLogger(__name__)


class MetricsManager:
    """
    Manages Prometheus metrics for the platform.
    Tracks agent execution times, token usage, and error rates.
    """

    def __init__(self) -> None:
        """Initializes the Prometheus metric definitions."""
        self.tasks_completed = Counter(
            "agent_tasks_completed_total",
            "Total number of engineering tasks completed",
            ["agent_role", "status"]
        )
        self.tokens_consumed = Counter(
            "agent_tokens_consumed_total",
            "Total LLM tokens consumed by the platform",
            ["model_name"]
        )
        self.task_duration = Histogram(
            "agent_task_duration_seconds",
            "Time spent completing a task node",
            ["agent_role"]
        )
        self._is_server_running = False

    def start_server(self, port: int = 9090) -> None:
        """
        Starts the Prometheus metrics exposition server.

        Args:
            port: The port to expose the /metrics endpoint on.
        """
        if not self._is_server_running:
            try:
                start_http_server(port)
                self._is_server_running = True
                logger.info(f"Prometheus metrics server started on port {port}.")
            except Exception as e:
                logger.error(f"Failed to start Prometheus server: {e}")

    def record_task_completion(self, agent_role: str, status: str) -> None:
        """Records a completed (or failed) task."""
        self.tasks_completed.labels(agent_role=agent_role, status=status).inc()

    def record_token_usage(self, model_name: str, tokens: int) -> None:
        """Records LLM token usage."""
        self.tokens_consumed.labels(model_name=model_name).inc(tokens)


if __name__ == "__main__":
    import time
    
    logging.basicConfig(level=logging.INFO)
    metrics = MetricsManager()
    metrics.start_server(port=9091)
    
    # Simulate agent work
    with metrics.task_duration.labels(agent_role="planner").time():
        logger.info("Simulating planner work...")
        time.sleep(0.5)
        
    metrics.record_task_completion(agent_role="planner", status="success")
    metrics.record_token_usage(model_name="llama3-70b-8192", tokens=150)
    
    logger.info("Metrics recorded. Access at http://localhost:9091/")