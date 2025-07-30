#!/bin/bash
# if you change this file and the places it looks for local paths:
# please also update the launch.json for vscode accordingly
# the things that must be kept in sync are KB_DEPLOYMENT_CONFIG and PYTHONPATH
#
# Two main options here:
# 1. run as `entrypoint.sh` - this starts the staging service webapp
# 2. run as `entrypoint.sh dts_watcher [--debug]` - this starts only the Data
#    transfer service file watcher. Optionally include --debug to print
#    debugging logs.

# top section for local running
DIR="$( cd "$( dirname "$0" )" && pwd )"
PROJECT_ROOT="$( cd "$DIR/../.." && pwd)"

if [ -d "$PROJECT_ROOT/staging_service" ]; then
    export PYTHONPATH="$PROJECT_ROOT"
    export KB_DEPLOYMENT_CONFIG="$DIR/../conf/local.cfg"
    WATCHER_PATH="$PROJECT_ROOT/scripts/run_dts_watcher.py"
fi

# bottom section for running inside docker
if [ -d "/kb/deployment/lib/staging_service" ]; then
    export PYTHONPATH="/kb/deployment/lib"
    WATCHER_PATH="/kb/deployment/scripts/run_dts_watcher.py"
    # environment variable for KB_DEPLOYMENT_CONFIG is expected to be set
    # when the container is started
fi

if [ "$1" == "dts_watcher" ]; then
    python3 "$WATCHER_PATH" $2
else
    python3 -m staging_service
fi
