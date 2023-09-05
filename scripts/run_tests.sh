#!/usr/bin/env bash

# DIR is the root of the project.
DIR="$( cd "$( dirname "$0" )" && pwd )/.."

export KB_DEPLOYMENT_CONFIG="${DIR}/deployment/conf/testing.cfg"
export FILE_LIFETIME="90"

# Tests are located in the `tests` directory. Specific tests or groups of 
# tests may be run by proving an argument to the script which is an acceptable
# test path spec for pytest. E.g. `./scripts/run_tests.sh tests/test_app.py` 
# will run just the tests in `tests/test_app.py`.
export TESTS="${1:-tests}"

echo
echo "****************************"
echo "**"
echo "** Running tests in ${TESTS}"
echo "**"
echo "****************************"
echo
python -m pytest -s -vv --cov=staging_service --cov-report term --cov-report html "${TESTS}"

