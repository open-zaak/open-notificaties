#!/bin/bash

set -e

LOGLEVEL=${CELERY_LOGLEVEL:-INFO}

# Figure out abspath of this script
SCRIPT=$(readlink -f "$0")
SCRIPTPATH=$(dirname "$SCRIPT")

# wait for required services
${SCRIPTPATH}/wait_for_db.sh

mkdir -p celerybeat

echo "Starting celery beat"
exec celery --app nrc.celery --workdir src beat \
    -l $LOGLEVEL \
    -s ../celerybeat/beat \
    --pidfile=  # empty on purpose to avoid a bug when rebooting redis : https://github.com/open-formulieren/open-forms/pull/1187
