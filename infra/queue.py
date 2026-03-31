import os
import logging
from celery import Celery

logger = logging.getLogger(__name__)

def create_celery_app() -> Celery:
    """
    Initializes and configures the Celery application.

    Returns:
        Celery: The configured Celery application instance.
    """
    broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

    app = Celery(
        "autonomous_engineer",
        broker=broker_url,
        backend=result_backend,
        include=["workers.agent_worker"]
    )

    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=3600,
    )

    return app

celery_app = create_celery_app()

if __name__ == "__main__":
    print(celery_app.conf.humanize(with_defaults=False, censored=True))
