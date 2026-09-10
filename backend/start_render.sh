#!/bin/sh
set -e

RAW="${REDIS_URL:-}"

if echo "$RAW" | grep -q "redis-cli"; then
  RAW="$(echo "$RAW" | sed -n 's/.*-u[[:space:]]*\([^[:space:]]*\).*/\1/p')"
fi

RAW="$(echo "$RAW" | tr -d ' ')"
RAW="$(echo "$RAW" | sed 's/^redis:\/\//rediss:\/\//')"

case "$RAW" in
  */0* ) : ;;
  * ) RAW="${RAW%/}/0" ;;
esac

if ! echo "$RAW" | grep -q "ssl_cert_reqs="; then
  if echo "$RAW" | grep -q "\?"; then
    RAW="$RAW&ssl_cert_reqs=CERT_NONE"
  else
    RAW="$RAW?ssl_cert_reqs=CERT_NONE"
  fi
fi

export CELERY_BROKER_URL="$RAW"
export CELERY_RESULT_BACKEND="$RAW"

if [ -z "$CELERY_BROKER_URL" ]; then
  echo "ERROR: REDIS_URL is empty/invalid"
  exit 1
fi

echo "BROKER=$CELERY_BROKER_URL"

# Verify Tesseract installed
echo "==> Tesseract version: $(tesseract --version 2>&1 | head -1)"

python -m celery -A app.workers.celery_app.celery_app worker \
  --loglevel=info \
  --queues=default \
  --concurrency=1 \
  --pool=solo \
  --max-tasks-per-child=10 \
  --without-gossip \
  --without-mingle \
  --without-heartbeat &

exec python -m uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}"