#!/bin/bash
# if you change this file and the places it looks for local paths:
# please also update the launch.json for vscode accordingly
# the things that must be kept in sync are KB_DEPLOYMENT_CONFIG and PYTHONPATH


if [ -d "kb/deployment/lib/staging_service" ]; then
   echo "staging_service not installed in /kb/deployment/lib as expected"
   exit 1
fi

PYTHONPATH="kb/deployment/lib/staging_service"

# disabled in favor of running behind gunicorn
# python3 -m staging_service

# The port at which to run this service.
# TODO: this should probably be 5000 in order to operate like other KBase services.
#       Who likes surprises like this?
SERVICE_PORT="${SERVICE_PORT:-3000}"

# See https://docs.gunicorn.org/en/latest/run.html
# Recommended to have 2-4 workers per core. Default assumes 1 core.
GUNICORN_WORKERS="${GUNICORN_WORKERS:-4}"

# Workers silent for more than this many seconds are killed and restarted.
# This setting affects the /upload endpoint, as it processes files after
# upload, calculating the md5 and potentially, in the future, additional tasks
# such as validating the file. 
# Other endpoints may encounter a delay as well, as any endpoint which access
# metadata may trigger a metadata rebuild, including the md5.
# Default to 10 minutes, a generous amount of time to wait for this to complete.
# Alternative designs could solve this in a different way.
GUNICORN_TIMEOUT="${GUNICORN_TIMEOUT:-600}"

# TODO: should be port 5000 to match other kbase services
gunicorn staging_service.main:web_app \
  --bind 0.0.0.0:"${SERVICE_PORT}" \
  --worker-class aiohttp.GunicornWebWorker \
  --pythonpath "${PYTHONPATH}" \
  --workers "${GUNICORN_WORKERS}" \
  --timeout "${GUNICORN_TIMEOUT}"