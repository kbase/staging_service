#!/bin/bash
DIR="$( cd "$( dirname "$0" )" && pwd )"
export KB_DEPLOYMENT_CONFIG="$DIR/deployment/conf/testing.cfg"
export FILE_LIFETIME="90"
export TESTS="${1:-tests}"
echo
echo "****************************"
echo "**"
echo "** Running tests in ${TESTS}"
echo "**"
echo "****************************"
echo
python3 -m pytest -s -vv --cov=staging_service --cov-report term --cov-report html $TESTS

