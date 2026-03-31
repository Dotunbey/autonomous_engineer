import logging
from typing import Any, Dict

from celery.schedules import crontab
from autonomous_engineer.infra.queue import celery_app

logger = logging.getLogger(__name__)


class JobScheduler:
    """
    Manages the registration of recurring agent jobs using Celery Beat.
    Useful for autonomous tasks like daily codebase linting or nightly dependency updates.
    """

    def __init__(self, app: Any) -> None:
        """
        Initializes the JobScheduler.

        Args:
            app: The Celery application instance.
        """
        self._app = app
        self._app.conf.beat_schedule = {}

    def schedule_daily_task(self, task_name: str, hour: int, minute: int, kwargs: Dict[str, Any]) -> None:
        """
        Schedules a task to run every day at a specific time.

        Args:
            task_name: The registered name of the Celery task.
            hour: The hour to execute (0-23).
            minute: The minute to execute (0-59).
            kwargs: Keyword arguments to pass to the task.
        """
        schedule_name = f"daily_{task_name}_{hour}_{minute}"
        self._app.conf.beat_schedule[schedule_name] = {
            "task": task_name,
            "schedule": crontab(hour=hour, minute=minute),
            "kwargs": kwargs,
        }
        logger.info(f"Scheduled {task_name} to run daily at {hour:02d}:{minute:02d} UTC.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    scheduler = JobScheduler(celery_app)
    
    # Example: Schedule a daily repository sweep at 2:30 AM UTC
    scheduler.schedule_daily_task(
        task_name="workers.agent_worker.execute_engineering_task",
        hour=2,
        minute=30,
        kwargs={"task_id": "cron_001", "goal": "Run full test suite and fix failing tests", "workspace": "/app"}
    )