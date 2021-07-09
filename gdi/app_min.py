from aiohttp import web

routes = web.RouteTableDef()


@routes.post("/upload")
async def upload(request: web.Request):
    reader = await request.multipart()
    user_file = await reader.next()

    filename: str = user_file.filename
    user_file.release()
    reader.release()
    return web.json_response({"filename": filename})


def app_factory():
    app = web.Application()
    app.router.add_routes(routes)
    return app
