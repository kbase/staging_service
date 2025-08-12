#!/bin/bash
# if you change this file and the places it looks for local paths:
# please also update the launch.json for vscode accordingly
# the things that must be kept in sync are KB_DEPLOYMENT_CONFIG and PYTHONPATH
#
# This entrypoint runs the Data Transfer Service file watcher.
# If run locally (outside of a container), it appends the PYTHONPATH with the
# staging service module.
# Running in a container assumes that the PYTHONPATH is already set.

DIR="$( cd "$( dirname "$0" )" && pwd )"
PROJECT_ROOT="$( cd "$DIR/../.." && pwd)"
WATCHER_PATH="/kb/deployment/scripts/run_dts_watcher.py"

if [ -d "$PROJECT_ROOT/staging_service" ]; then
    export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
    export KB_DEPLOYMENT_CONFIG="$DIR/../conf/local.cfg"
    WATCHER_PATH="$PROJECT_ROOT/scripts/run_dts_watcher.py"
fi

python3 "$WATCHER_PATH" $@
