#!/bin/sh
set -e

# Accept REDIS_URL in 2 forms:
# 1) rediss://default:PASS@host:6379/0
# 2) redis-cli --tls -u redis://default:PASS@host:6379

RAW="${REDIS_URL:-}"

# If user pasted redis-cli command, extract the URL after -u
if echo "$RAW" | grep -q "redis-cli"; then
  RAW="$(echo "$RAW" | sed -n 's/.*-u[[:space:]]*\([^[:space:]]*\).*/\1/p')"
fi

# Trim spaces
RAW="$(echo "$RAW" | tr -d ' ')"

# Convert redis:// -> rediss:// for TLS
RAW="$(echo "$RAW" | sed 's/^redis:\/\//rediss:\/\//')"

# Ensure DB path /0 exists
case "$RAW" in
  */0* ) : ;;
  * ) RAW="${RAW%/}/0" ;;
esac

# Ensure ssl_cert_reqs present (Celery requires for rediss)
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

python -m celery -A app.workers.celery_app.celery_app worker \
  --loglevel=info \
  --queues=default \
  --concurrency=1 \
  --pool=solo \
  --max-tasks-per-child=1 \
  --without-gossip \
  --without-mingle \
  --without-heartbeat &

exec python -m uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}"