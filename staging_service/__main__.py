from .app import app_factory
from aiohttp import web
import asyncio
import os
import uvloop
import configparser
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())  # for speed of event loop

config = configparser.ConfigParser()
config.read(os.environ['KB_DEPLOYMENT_CONFIG'])
web.run_app(app_factory(config), port=3000)