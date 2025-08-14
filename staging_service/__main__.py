import asyncio
import os

import uvloop
from aiohttp import web

from .app import app_factory
from staging_service.config import StagingServiceConfig

CONFIG_ENV = "KB_DEPLOYMENT_CONFIG"

if CONFIG_ENV not in os.environ:
    raise FileNotFoundError(f"Missing required config environment variable: {CONFIG_ENV}")

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())  # for speed of event loop

config = StagingServiceConfig(os.environ.get("KB_DEPLOYMENT_CONFIG"))
app = asyncio.run(app_factory(config))
web.run_app(app, port=3000)
