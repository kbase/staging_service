from aiohttp import web
import aiohttp_cors
import os
from .metadata import stat_data, some_metadata, dir_info
import shutil
from .utils import Path
from .auth2Client import KBaseAuth2
from .globus import assert_globusid_exists, is_globusid

routes = web.RouteTableDef()


@routes.get('/test-service')
async def test_service(request: web.Request):
    """
    @apiName test-service
    @apiSampleRequest /test-server/
    @apiSuccess {json} string Should return code 200 with string
    "This is just a test. This is only a test.
    """
    return web.Response(text='This is just a test. This is only a test.')


@routes.get('/test-auth')
async def test_auth(request: web.Request):
    username = await auth_client.get_user(request.headers['Authorization'])
    return web.Response(text="I'm authenticated as {}".format(username))


@routes.get('/list/{path:.*}')
async def list_files(request: web.Request):
    """
    {get} /list/:path list files/folders in path
    @apiParam {string} path path to directory
    @apiParam {string} ?type=(folder|file) only fetch folders or files

    @apiSuccess {json} meta metadata for listed objects
    @apiSuccessExample {json} Success-Response:
    HTTP/1.1 200 OK
     [
      {
          name: "blue-panda",
          mtime: 1459822597000,
          size: 476
      }, {
          name: "blue-zebra",
         mtime: 1458347601000,
          size: 170,
          isFolder: true
      }
    ]
    """
    token = request.headers['Authorization']
    username = await auth_client.get_user(token)
    await assert_globusid_exists(username, token)
    path = Path.validate_path(username, request.match_info['path'])

    if not os.path.exists(path.full_path):
        raise web.HTTPNotFound(text='path {path} does not exist'.format(path=path.user_path))
    try:
        show_hidden = request.query['showHidden']
        if 'true' == show_hidden or 'True' == show_hidden:
            show_hidden = True
        else:
            show_hidden = False
    except KeyError as no_query:
        show_hidden = False
    return web.json_response(await dir_info(path.full_path, show_hidden, recurse=False))


@routes.get('/search/{query:.*}')
async def search(request: web.Request):
    username = await auth_client.get_user(request.headers['Authorization'])
    query = request.match_info['query']
    user_dir = Path.validate_path(username)
    try:
        show_hidden = request.query['showHidden']
        if 'true' == show_hidden or 'True' == show_hidden:
            show_hidden = True
        else:
            show_hidden = False
    except KeyError as no_query:
        show_hidden = False
    results = await dir_info(user_dir.full_path, show_hidden, query)
    results.sort(key=lambda x: x['mtime'], reverse=True)
    return web.json_response(results)


@routes.get('/metadata/{path:.*}')
async def get_metadata(request: web.Request):
    username = await auth_client.get_user(request.headers['Authorization'])
    path = Path.validate_path(username, request.match_info['path'])
    if not os.path.exists(path.full_path):
        raise web.HTTPNotFound(text='path {path} does not exist'.format(path=path.user_path))
    return web.json_response(await some_metadata(path))


@routes.post('/upload')
async def upload_files_chunked(request: web.Request):
    """
    @api {post} /upload post endpoint to upload data
    @apiName upload
    @apiSampleRequest /upload/
    @apiSuccess {json} meta meta on data uploaded
    @apiSuccessExample {json} Success-Response:
        HTTP/1.1 200 OK
        [{
    "path": "/nconrad/Athaliana.TAIR10_GeneAtlas_Experiments.tsv",
    "size": 3190639,
    "encoding": "7bit",
    "name": "Athaliana.TAIR10_GeneAtlas_Experiments.tsv"
    }, {
    "path": "/nconrad/Sandbox_Experiments-1.tsv",
    "size": 4309,
    "encoding": "7bit",
    "name": "Sandbox_Experiments-1.tsv"
    }]
    """
    token = request.headers['Authorization']
    username = await auth_client.get_user(token)
    await assert_globusid_exists(username, token)
    reader = await request.multipart()
    counter = 0
    while counter < 100:  # TODO this is arbitrary to keep an attacker from creating infinite loop
        # This loop handles the null parts that come in inbetween destpath and file
        part = await reader.next()
        if part.name == 'destPath':
            destPath = await part.text()
        elif part.name == 'uploads':
            user_file = part
            break
        else:
            counter += 1
    filename: str = user_file.filename
    size = 0
    destPath = os.path.join(destPath, filename)
    path = Path.validate_path(username, destPath)
    os.makedirs(os.path.dirname(path.full_path), exist_ok=True)
    with open(path.full_path, 'wb') as f:  # TODO should we handle partial file uploads?
        while True:
            chunk = await user_file.read_chunk()
            if not chunk:
                break
            size += len(chunk)
            f.write(chunk)
    response = await stat_data(path.full_path)
    return web.json_response([response])


@routes.delete('/delete/{path:.+}')
async def delete(request: web.Request):
    """
    allows deletion of both directories and files
    """
    username = await auth_client.get_user(request.headers['Authorization'])
    path = Path.validate_path(username, request.match_info['path'])
    # make sure directory isn't home
    if path.user_path == username:
        raise web.HTTPForbidden(text='cannot delete home directory')
    if is_globusid(path, username):
        raise web.HTTPForbidden(text='cannot delete protected file')
    if os.path.isfile(path.full_path):
        os.remove(path.full_path)
        if os.path.exists(path.metadata_path):
            os.remove(path.metadata_path)
    elif os.path.isdir(path.full_path):
        shutil.rmtree(path.full_path)
        if os.path.exists(path.metadata_path):
            shutil.rmtree(path.metadata_path)
    else:
        raise web.HTTPNotFound(text='could not delete {path}'.format(path=path.user_path))
    return web.Response(text='successfully deleted {path}'.format(path=path.user_path))


@routes.patch('/mv/{path:.+}')
async def rename(request: web.Request):
    username = await auth_client.get_user(request.headers['Authorization'])
    path = Path.validate_path(username, request.match_info['path'])
    # make sure directory isn't home
    if path.user_path == username:
        raise web.HTTPForbidden(text='cannot rename home directory')
    if is_globusid(path, username):
        raise web.HTTPForbidden(text='cannot rename protected file')
    body = await request.post()
    new_path = body['newPath']
    new_path = Path.validate_path(username, new_path)
    if os.path.exists(path.full_path):
        if not os.path.exists(new_path.full_path):
            shutil.move(path.full_path, new_path.full_path)
            if os.path.exists(path.metadata_path):
                shutil.move(path.metadata_path, new_path.metadata_path)
        else:
            raise web.HTTPConflict(
                text='{new_path} allready exists'.format(new_path=new_path.user_path))
    else:
        raise web.HTTPNotFound(text='{path} not found'.format(path=path.user_path))
    return web.Response(text='successfully moved {path} to {new_path}'
                        .format(path=path.user_path, new_path=new_path.user_path))


def app_factory(config):
    app = web.Application()
    app.router.add_routes(routes)
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
            )
    })
    # Configure CORS on all routes.
    for route in list(app.router.routes()):
        cors.add(route)
    # TODO this is pretty hacky dependency injection
    # potentially some type of code restructure would allow this without a bunch of globals
    Path._DATA_DIR = config['staging_service']['DATA_DIR']
    Path._META_DIR = config['staging_service']['META_DIR']
    global auth_client
    auth_client = KBaseAuth2(config['staging_service']['AUTH_URL'])
    return app
