#!infra/queue.py
import os
import logging
from celery import Celery

logger = logging.getLogger(__name__)

def create_celery_app() -> Celery:
    """
    Initializes and configures the Celery application with SSL support for Upstash.

    Returns:
        Celery: The configured Celery application instance.
    """
    broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

    # FIX: Handle SSL requirements for rediss:// (Upstash/Managed Redis)
    # The error 'A rediss:// URL must have parameter ssl_cert_reqs' is solved by
    # explicitly passing the SSL context via broker_use_ssl and transport_options.
    ssl_options = None
    if broker_url.startswith("rediss://"):
        ssl_options = {
            "ssl_cert_reqs": "none" # Some environments require 'CERT_NONE' or 'none'
        }

    app = Celery(
        "autonomous_engineer",
        broker=broker_url,
        backend=result_backend,
        include=["workers.agent_worker"]
    )

    app.conf.update(
        broker_use_ssl=ssl_options,
        redis_backend_use_ssl=ssl_options,
        # Transport options are critical for some Redis driver versions to recognize SSL settings
        broker_transport_options={
            "ssl": ssl_options
        },
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=3600,
        # Render Free Tier Fix: Use solo pool to save memory
        worker_pool='solo'
    )

    return app

celery_app = create_celery_app()

if __name__ == "__main__":
    print(celery_app.conf.humanize(with_defaults=False, censored=True))
