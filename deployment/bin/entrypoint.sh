#!/usr/bin/env bash

#
# This is the production entrypoint, whose sole job is to start the service.
# The service starts via staging_service/__main__.py which is why the python
# invocation below references the staging_service directory.
#

export PYTHONPATH="/kb/deployment/lib"
python -m staging_service