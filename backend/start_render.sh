#!/bin/sh
set -e

# Celery worker in background (low memory)
python -m celery -A app.workers.celery_app.celery_app worker \
  --loglevel=info --queues=default \
  --concurrency=1 --pool=solo \
  --without-gossip --without-mingle --without-heartbeat &

# API in foreground
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
