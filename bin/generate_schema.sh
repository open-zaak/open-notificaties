#!/bin/bash

# Run this script from the root of the repository

set -e

OUTPUT_FILE=$1

if [[ -z "$VIRTUAL_ENV" ]] && [[ ! -v GITHUB_ACTIONS ]]; then
    echo "You need to activate your virtual env before running this script"
    exit 1
fi

echo "Generating OAS schema"
src/manage.py spectacular \
    --file ${OUTPUT_FILE:-./src/openapi.yaml} \
    --validate \
    --lang="nl-nl"
