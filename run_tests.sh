DIR="$( cd "$( dirname "$0" )" && pwd )"
export KB_DEPLOYMENT_CONFIG="$DIR/deployment/conf/testing.cfg"
python3 -m pytest --cov=staging_service