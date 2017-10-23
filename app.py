from aiohttp import web
#TODO see if uvloop helps at all
# import uvloop
# import asyncio
from os import path
from time import time
from auth2Client import KBaseAuth2
# asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


auth_client = KBaseAuth2()


async def test_service(request: web.Request):
    """
    @apiName test-service
    @apiSampleRequest /test-server/
    @apiSuccess {json} string Should return code 200 with string
    "This is just a test. This is only a test.
    """
    return web.Response(text='This is just a test. This is only a test.')


async def test_auth(request: web.Request):
    pass


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
    pass


async def search(request: web.Request):
    pass


def validate_path(username: str, path: str):
    """
    @returns a path based on path that must start with username
    throws an exeception for an invalid path or username"""
    # TODO check that the username supplied is the one for authenticated user
    start = path.find(username)
    if start == -1:
        raise ValueError()
    return path[start:]


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
    filename = user_file.filename
    size = 0
    try:
        destPath = validate_path(username, destPath)
    except ValueError as error:
        return "ivalid  username"
    with open(path.join('./data/bulk', destPath, filename), 'wb') as f:
        while True:
            chunk = await user_file.read_chunk()
            if not chunk:
                break
            size += len(chunk)
            f.write(chunk)
    return web.Response(text='stuff got stored' + str(start-time()))


app = web.Application()
# Get routes
app.router.add_get('/test-service', test_service)
app.router.add_get('/test-auth', test_auth)
app.router.add_get('/list/*', list_files)
app.router.add_get('/search/*', search)
# Post routes
app.router.add_post('/upload', upload_files_chunked)
# Run server
web.run_app(app)