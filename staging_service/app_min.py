from aiohttp import web

routes = web.RouteTableDef()


@routes.post("/upload")
async def upload_files_chunked(request: web.Request):
    reader = await request.multipart()
    user_file = await reader.next()

    filename: str = user_file.filename
    if filename.lstrip() != filename:
        raise web.HTTPBadRequest( 
            text="cannot upload file with name beginning with space"
        )
    return web.json_response({"filename": filename})


def app_factory():
    app = web.Application()
    app.router.add_routes(routes)
    return app
