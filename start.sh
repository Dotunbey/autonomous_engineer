#!/bin/bash

export PYTHONPATH=.

# 1. Start the Celery worker in the background
# Pointing directly to infra.queue because infra/ is at the root of the repo
celery -A infra.queue worker --loglevel=info &

# 2. Start the FastAPI server in the foreground
# Pointing directly to api.server because api/ is at the root of the repo
uvicorn api.server:app --host 0.0.0.0 --port ${PORT:-8000}
