from aiohttp import web
#TODO see if uvloop helps at all
# import uvloop
# import asyncio
import os
from time import time
from auth2Client import KBaseAuth2
# asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

auth_client = KBaseAuth2()
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
    try:
        username = auth_client.get_user(request.headers['Authorization'])
    except ValueError as bad_auth:
        return web.json_response({'error': 'Unable to validate authentication credentials'})
    return web.Response(text="I'm authenticated as {}".format(username))


def validate_path(username: str, path: str) -> str:
    """
    @returns a path based on path that must start with username
    throws an exeception for an invalid path or username
    starts path at first occurance of username"""
    path = os.path.normpath(path)
    start = path.find(username)
    if start == -1:
        raise ValueError('username not in path')
    return path[start:]


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
        username = auth_client.get_user(request.headers['Authorization'])
    except ValueError as bad_auth:
        return web.json_response({'error': 'Unable to validate authentication credentials'})
    try:
        validated_path = validate_path(username, request.match_info['path'])
    except ValueError as bad_path:
        return web.json_response({'error': 'badly formed path'})
    full_path = os.path.join('./data/bulk', validated_path)
    if not os.path.exists(full_path):
        return web.json_response({'error': 'path {path} does not exist'.format(path=validated_path)})
    _, dirnames, filenames = next(os.walk(full_path))
    # make json for each dirnames and filenames
    response = []
    for filename in filenames:
        filepath = os.path.join(validated_path, filename)
        file_stats = os.stat(os.path.join(full_path, filename))
        response.append(
            {
                'name': filename,
                'path': filepath,
                'mtime': int(file_stats.st_mtime*1000),  # given in seconds, want ms
                'size': file_stats.st_size,
                'isFolder': False
            }
        )
    for dirname in dirnames:
        dirpath = os.path.join(validate_path, dirname)
        dir_stats = os.stat(os.path.join(full_path, dirname))
        response.append(
            {
                'name': dirname,
                'path': dirpath,
                'mtime': int(dir_stats.st_mtime*1000),  # given in seconds, want ms
                'size': dir_stats.st_size,
                'isFolder': True
            }
        )
    # transform list of dicts into json
    
    return web.json_response(response)


@routes.get('/search/{query}')
async def search(request: web.Request):
    pass

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
    start = time()

    reader = await request.multipart()
    # TODO validate path inputs and filename inputs so it goes where it should go
    while True:
        part = await reader.next()
        if part.name == 'username':
            username = 'nixonpjoshua'
        elif part.name == 'destPath':
            destPath = '/nixonpjoshua'
        elif part.name == 'uploads':
            user_file = part
            break
        else:
            return "error you didnt follow the API spec"
    filename: str = user_file.filename
    size = 0
    try:
        destPath = validate_path(username, destPath)
    except ValueError as error:
        return "ivalid  username"
    with open(os.path.join('./data/bulk', destPath, filename), 'wb') as f:
        while True:
            chunk = await user_file.read_chunk()
            if not chunk:
                break
            size += len(chunk)
            f.write(chunk)
    return web.Response(text='stuff got stored' + str(start-time()))


app = web.Application()
app.router.add_routes(routes)
web.run_app(app, port=3000)
