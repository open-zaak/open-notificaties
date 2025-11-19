#!/bin/bash

set -e

# Set defaults for OTEL
export OTEL_SERVICE_NAME="${OTEL_SERVICE_NAME:-opennotificaties-flower}"

exec celery --app nrc --workdir src flower
