#!/bin/bash

set -euo pipefail

LOGLEVEL=${CELERY_LOGLEVEL:-INFO}

QUEUE=${CELERY_WORKER_QUEUE:=celery}
WORKER_NAME=${CELERY_WORKER_NAME:="${QUEUE}"@%n}

# Figure out abspath of this script
SCRIPT=$(readlink -f "$0")
SCRIPTPATH=$(dirname "$SCRIPT")

# wait for required services
${SCRIPTPATH}/wait_for_db.sh

# build up worker options array
worker_options=(
    "-Q$QUEUE"
    "-n$WORKER_NAME"
    "-l$LOGLEVEL"
    "-Ofair"
)

if [[ -v CELERY_WORKER_CONCURRENCY ]]; then
    echo "Using concurrency ${CELERY_WORKER_CONCURRENCY}"
    # Use threads for concurrency, because Open Notificaties is I/O bound
    # and you can easily run a lot of threads without increasing the memory footprint
    # of the Celery worker (which does happen when you run with prefork)
    worker_options+=( "-c${CELERY_WORKER_CONCURRENCY}" "--pool=threads" )
fi
# Set defaults for OTEL
export OTEL_SERVICE_NAME="${OTEL_SERVICE_NAME:-opennotificaties-worker-"${QUEUE}"}"

echo "Starting celery worker $WORKER_NAME with queue $QUEUE"
# unset this if NOT using a process pool
export _OTEL_DEFER_SETUP="true"
exec celery \
    --app nrc \
    --workdir src \
    worker "${worker_options[@]}" \
    -E \
    --max-tasks-per-child=50
