#!/bin/sh

set -e

celery --app nrc --workdir src flower
