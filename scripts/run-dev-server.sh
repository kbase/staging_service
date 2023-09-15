#!/usr/bin/env bash

FILE_LIFETIME="90" KB_DEPLOYMENT_CONFIG="${PWD}/deployment/conf/local.cfg" PYTHONPATH="${PWD}/staging_service" python -m staging_service
