import asyncio
import configparser
import os

import uvloop
from aiohttp import web

from .app import app_factory

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())  # for speed of event loop

config = configparser.ConfigParser()
config.read(os.environ["KB_DEPLOYMENT_CONFIG"])
app = asyncio.run(app_factory(config))
web.run_app(app, port=3000)
