#!/bin/bash

set -e

exec celery --app nrc --workdir src flower
