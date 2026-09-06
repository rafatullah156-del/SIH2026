#!/usr/bin/env bash
set -e

# run celery in background (single process, low memory friendly)
python -m celery -A app.workers.celery_app.celery_app worker \
  --loglevel=info --queues=default \
  --concurrency=1 --pool=solo \
  --without-gossip --without-mingle --without-heartbeat &

# run api in foreground
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
