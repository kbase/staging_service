from aiohttp import web
import aiohttp_cors
#  TODO see if uvloop helps at all
import uvloop
import asyncio
import os
from metadata import stat_data, some_metadata
import shutil
from utils import Path
from auth2Client import KBaseAuth2
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

auth_client = KBaseAuth2()
routes = web.RouteTableDef()


# TODO use pep 471 ??
async def dir_info(path: Path, query: str = '', recurse=True) -> list:
    response = []
    for root, dirs, files in os.walk(path.full_path):
        for filename in files:
            full_path = os.path.join(root, filename)
            if full_path.find(query) != -1:  # TODO fuzzy wuzzy matching??
                response.append(await stat_data(full_path))
        for dirname in dirs:
            full_path = os.path.join(root, dirname)
            if full_path.find(query) != -1:  # TODO fuzzy wuzzy matching??
                response.append(await stat_data(full_path, isFolder=True))
        if recurse is False:
            break
    return response


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
    try:
        username = await auth_client.get_user(request.headers['Authorization'])
    except ValueError as bad_auth:
        return web.json_response({'error': 'Unable to validate authentication credentials'})
    return web.Response(text="I'm authenticated as {}".format(username))


@routes.get('/list/{path:.+}')
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
    try:
        username = await auth_client.get_user(request.headers['Authorization'])
    except ValueError as bad_auth:
        return web.json_response({'error': 'Unable to validate authentication credentials'})
    try:
        path = Path.validate_path(username, request.match_info['path'])
    except ValueError as bad_path:
        return web.json_response({'error': 'badly formed path'})
    if not os.path.exists(path.full_path):
        return web.json_response({
            'error': 'path {path} does not exist'.format(path=path.user_path)
        })
    return web.json_response(await dir_info(path, recurse=False))


@routes.get('/search/{query:.*}')
async def search(request: web.Request):
    try:
        username = await auth_client.get_user(request.headers['Authorization'])
    except ValueError as bad_auth:
        return web.json_response({'error': 'Unable to validate authentication credentials'})
    query = request.match_info['query']
    user_dir = Path.validate_path(username, username)
    results = await dir_info(user_dir, query)
    results.sort(key=lambda x: x['mtime'], reverse=True)
    return web.json_response(results)


@routes.get('/metadata/{path:.*}')
async def get_metadata(request: web.Request):
    try:
        username = await auth_client.get_user(request.headers['Authorization'])
    except ValueError as bad_auth:
        return web.json_response({'error': 'Unable to validate authentication credentials'})
    try:
        path = Path.validate_path(username, request.match_info['path'])
    except ValueError as bad_path:
        return web.json_response({'error': 'badly formed path'})
    if not os.path.exists(path.full_path):
        return web.json_response({
            'error': 'path {path} does not exist'.format(path=path.user_path)
        })
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
    try:
        username = await auth_client.get_user(request.headers['Authorization'])
    except ValueError as bad_auth:
        return web.json_response({'error': 'Unable to validate authentication credentials'})
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
    try:
        path = Path.validate_path(username, destPath)
    except ValueError as error:
        return web.json_response({'error': 'invalid destination for file for user'})
    with open(path.full_path, 'wb') as f:
        while True:
            chunk = await user_file.read_chunk()
            if not chunk:
                break
            size += len(chunk)
            f.write(chunk)
    response = await stat_data(path.full_path)
    return web.json_response([response])


@routes.post('/delete/{path:.+}')
async def delete(request: web.Request):
    """
    allows deletion of both directories and 
    """
    try:
        username = await auth_client.get_user(request.headers['Authorization'])
    except ValueError as bad_auth:
        return web.json_response({'error': 'Unable to validate authentication credentials'})
    try:
        path = Path.validate_path(username, request.match_info['path'])
    except ValueError as bad_path:
        return web.json_response({'error': 'badly formed path'})
    # make sure directory isn't home
    if path.user_path == username:
        return web.json_response({'error': 'cannot delete home directory'})
    if os.path.isfile(path.full_path):
        os.remove(path.full_path)
        if os.path.exists(path.metadata_path):
            os.remove(path.metadata_path)
    elif os.path.isdir(path.full_path):
        shutil.rmtree(path.full_path)
        if os.path.exists(path.metadata_path):
            shutil.rmtree(path.metadata_path)
    else:
        return web.json_response({'error': 'could not delete {path}'.format(path=path.user_path)})
    return web.Response(text='successfully deleted {path}'.format(path=path.user_path))


@routes.post('/rename/{path:.+}')
async def rename(request: web.Request):
    try:
        username = await auth_client.get_user(request.headers['Authorization'])
    except ValueError as bad_auth:
        return web.json_response({'error': 'Unable to validate authentication credentials'})
    try:
        path = Path.validate_path(username, request.match_info['path'])
    except ValueError as bad_path:
        return web.json_response({'error': 'badly formed path'})
    # make sure directory isn't home
    if path.user_path == username:
        return web.json_response({'error': 'cannot rename home directory'})    
    body = await request.post()
    new_name = body['newName']
    # TODO new_name should be sanitized
    shutil.move(path.full_path, new_name)
    if os.path.exists(path.metadata_path):
        if os.path.isfile(path.metadata_path):
            shutil.move(path.metadata_path, new_name + '.json')
        else:
            shutil.move(path.metadata_path, new_name)
    return web.Response(text='successfully renamed {path}'.format(path=path.user_path))


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
web.run_app(app, port=3000)
