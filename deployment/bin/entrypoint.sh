#!/bin/bash
# if you change this file and the places it looks for local paths:
# please also update the launch.json for vscode accordingly
# the things that must be kept in sync are KB_DEPLOYMENT_CONFIG and PYTHONPATH

#top section for local running
DIR="$( cd "$( dirname "$0" )" && pwd )"
if [ -d "$DIR/../../staging_service" ]; then
    PYTHONPATH="$DIR/../../staging_service"
    export KB_DEPLOYMENT_CONFIG="$DIR/../conf/local.cfg"
    export FILE_LIFETIME="90"
fi

#bottom section for running inside docker
if [ -d "kb/deployment/lib/staging_service" ]; then
    PYTHONPATH="kb/deployment/lib/staging_service"
    # environment variable for KB_DEPLOYMENT_CONFIG set in docker-compose.yml
fi
python3 -m staging_service