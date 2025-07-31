#!/bin/bash
# if you change this file and the places it looks for local paths:
# please also update the launch.json for vscode accordingly
# the things that must be kept in sync are KB_DEPLOYMENT_CONFIG and PYTHONPATH
#
# This entrypoint runs the staging service webapp.
# If run locally (outside of a container), it appends the PYTHONPATH with the
# staging service module.
# Running in a container assumes that the PYTHONPATH is already set.

DIR="$( cd "$( dirname "$0" )" && pwd )"
PROJECT_ROOT="$( cd "$DIR/../.." && pwd)"

if [ -d "$PROJECT_ROOT/staging_service" ]; then
    export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
    export KB_DEPLOYMENT_CONFIG="$DIR/../conf/local.cfg"
fi

python3 -m staging_service
