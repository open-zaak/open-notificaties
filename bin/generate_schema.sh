#!/bin/bash

# Run this script from the root of the repository

set -e

if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "You need to activate your virtual env before running this script"
    exit 1
fi

echo "Generating OAS schema"
src/manage.py spectacular \
    --file ./src/openapi.yaml

#echo "Generating autorisaties.md"
#src/manage.py generate_autorisaties --output-file ./src/autorisaties.md

#echo "Generating notificaties.md"
#src/manage.py generate_notificaties --output-file ./src/notificaties.md
