import asyncio
# import configparser
# import os

import uvloop

from staging_service.app import app_factory

# from aiohttp import web

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())  # for speed of event loop

# config = configparser.ConfigParser()
# config.read(os.environ["KB_DEPLOYMENT_CONFIG"])
# web.run_app(app_factory(config), port=5000)


async def web_app():
    return app_factory()
