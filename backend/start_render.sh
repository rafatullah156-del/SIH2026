#!/bin/sh
set -e

# If CELERY_* not set, fall back to REDIS_URL
: "${CELERY_BROKER_URL:=${REDIS_URL}}"
: "${CELERY_RESULT_BACKEND:=${REDIS_URL}}"

# fail fast if still empty
if [ -z "$CELERY_BROKER_URL" ]; then
  echo "ERROR: CELERY_BROKER_URL/REDIS_URL is empty"
  exit 1
fi

echo "BROKER=$CELERY_BROKER_URL"

python -m celery -A app.workers.celery_app.celery_app worker \
  --loglevel=info --queues=default \
  --concurrency=1 --pool=solo \
  --without-gossip --without-mingle --without-heartbeat &

exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
