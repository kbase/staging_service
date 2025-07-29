#!/bin/bash
# if you change this file and the places it looks for local paths:
# please also update the launch.json for vscode accordingly
# the things that must be kept in sync are KB_DEPLOYMENT_CONFIG and PYTHONPATH

#top section for local running
DIR="$( cd "$( dirname "$0" )" && pwd )"
PROJECT_ROOT="$( cd "$DIR/../.." && pwd)"

if [ -d "$PROJECT_ROOT/staging_service" ]; then
    export PYTHONPATH="$PROJECT_ROOT"
    export KB_DEPLOYMENT_CONFIG="$DIR/../conf/local.cfg"
    WATCHER_PATH="$PROJECT_ROOT/scripts/run_dts_watcher.py"
fi

#bottom section for running inside docker
if [ -d "/kb/deployment/lib/staging_service" ]; then
    export PYTHONPATH="/kb/deployment/lib"
    WATCHER_PATH="/kb/deployment/scripts/run_dts_watcher.py"
    # environment variable for KB_DEPLOYMENT_CONFIG set in docker-compose.yml
fi

echo "PYTHONPATH: $PYTHONPATH"
echo "CONFIG: $KB_DEPLOYMENT_CONFIG"
echo "WATCHER_PATH: $WATCHER_PATH"

if [ "$1" == "dts_watcher" ]; then
    python3 "$WATCHER_PATH"
else
    python3 -m staging_service
fi
