#!/bin/bash

set -e

LOGLEVEL=${CELERY_LOGLEVEL:-INFO}

mkdir -p celerybeat

echo "Starting celery beat"
exec celery --app nrc --workdir src beat \
    -l $LOGLEVEL \
    -s ../celerybeat/beat \
    --pidfile=  # empty on purpose to avoid a bug when rebooting redis : https://github.com/open-formulieren/open-forms/pull/1187
