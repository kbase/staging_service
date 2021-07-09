#!/bin/bash
DIR="$( cd "$( dirname "$0" )" && pwd )"
export KB_DEPLOYMENT_CONFIG="$DIR/deployment/conf/testing.cfg"
export FILE_LIFETIME="90"
python3 -m pytest -s --cov=staging_service tests/test_app_min.py