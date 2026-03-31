#!infra/queue.py
import os
import logging
from celery import Celery

logger = logging.getLogger(__name__)

def create_celery_app() -> Celery:
    """
    Initializes and configures the Celery application with SSL support for Upstash.
    """
    broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

    # SSL Handling for Upstash (rediss://)
    ssl_options = None
    if broker_url.startswith("rediss://"):
        ssl_options = {"ssl_cert_reqs": "none"}

    app = Celery(
        "autonomous_engineer",
        broker=broker_url,
        backend=result_backend,
        include=["workers.agent_worker"]
    )

    app.conf.update(
        broker_use_ssl=ssl_options,
        redis_backend_use_ssl=ssl_options,
        broker_transport_options={"ssl": ssl_options},
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=3600,
        worker_pool='solo',
        broker_connection_retry_on_startup=True
    )

    return app

celery_app = create_celery_app()