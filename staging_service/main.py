import asyncio

import uvloop

from staging_service.app import app_factory

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())  # for speed of event loop


async def web_app():
    """
    The gunicorn web app factory function, which in turn just calls the
    aiohttp web server factory.
    """
    return app_factory()
