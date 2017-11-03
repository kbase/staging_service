from .app import app_factory
from aiohttp import web
import asyncio
import uvloop
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())  # for speed of event loop
web.run_app(app_factory(), port=3000)