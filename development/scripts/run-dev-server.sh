#!/bin/bash

echo "Running server in development..."
docker compose \
    -f development/docker-compose-kbase-ui.yml \
    --project-directory "${PWD}" \
    run  --rm staging_service