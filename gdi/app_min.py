from aiohttp import web

routes = web.RouteTableDef()


@routes.post("/thing")
async def thing(request: web.Request):
    # await request.release()
    return web.json_response({"hey": "there"})


def app_factory():
    app = web.Application()
    app.router.add_routes(routes)
    return app
