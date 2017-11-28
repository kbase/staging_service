from aiohttp import web
import aiohttp_cors
import os
from .metadata import stat_data, some_metadata, dir_info, add_upa
import shutil
from .utils import Path, run_command
from .auth2Client import KBaseAuth2
from .globus import assert_globusid_exists, is_globusid
from .JGIMetadata import read_metadata_for, translate_for_importer

routes = web.RouteTableDef()


@routes.get('/test-service')
async def test_service(request: web.Request):
    return web.Response(text='This is just a test. This is only a test.')


@routes.get('/test-auth')
async def test_auth(request: web.Request):
    username = await auth_client.get_user(request.headers['Authorization'])
    return web.Response(text="I'm authenticated as {}".format(username))


@routes.get('/file-lifetime')
async def file_lifetime(parameter_list):
    return web.Response(text=os.environ['FILE_LIFETIME'])


@routes.get('/existance/{path:.*}')
async def file_exists(request: web.Request):
    token = request.headers['Authorization']
    username = await auth_client.get_user(token)
    path = Path.validate_path(username, request.match_info['path'])
    exists = os.path.exists(path.full_path)
    isFile = os.path.isfile()
    return web.json_response({'exists': exists, 'isFile': isFile})


@routes.get('/list/{path:.*}')
async def list_files(request: web.Request):
    """
    lists the contents of a directory and some details about them
    """
    token = request.headers['Authorization']
    username = await auth_client.get_user(token)
    await assert_globusid_exists(username, token)
    path = Path.validate_path(username, request.match_info['path'])
    if not os.path.exists(path.full_path):
        raise web.HTTPNotFound(text='path {path} does not exist'.format(path=path.user_path))
    elif os.path.isfile(path.full_path):
        raise web.HTTPBadRequest(
            text='{path} is a file not a directory'.format(path=path.full_path)
        )
    try:
        show_hidden = request.query['showHidden']
        if 'true' == show_hidden or 'True' == show_hidden:
            show_hidden = True
        else:
            show_hidden = False
    except KeyError as no_query:
        show_hidden = False
    data = await dir_info(path, show_hidden, recurse=False)
    return web.json_response(data)


@routes.get('/search/{query:.*}')
async def search(request: web.Request):
    """
    returns all files and folders matching the search query ordered by modified date
    """
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
    results = await dir_info(user_dir, show_hidden, query)
    results.sort(key=lambda x: x['mtime'], reverse=True)
    return web.json_response(results)


@routes.get('/metadata/{path:.*}')
async def get_metadata(request: web.Request):
    """
    creates a metadate file for the file requested and returns its json contents
    if it's a folder it returns stat data about the folder
    """
    username = await auth_client.get_user(request.headers['Authorization'])
    path = Path.validate_path(username, request.match_info['path'])
    if not os.path.exists(path.full_path):
        raise web.HTTPNotFound(text='path {path} does not exist'.format(path=path.user_path))
    return web.json_response(await some_metadata(path))


@routes.get('/jgi-metadata/{path:.*}')
async def get_jgi_metadata(request: web.Request):
    """
    returns jgi metadata if associated with a file
    """
    username = await auth_client.get_user(request.headers['Authorization'])
    path = Path.validate_path(username, request.match_info['path'])
    return web.json_response(await read_metadata_for(path))


@routes.get('/impoter-defaults/{path:.*}')
async def get_impoter_defaults(request: web.Request):
    """
    tried to automatically populate an importer's fields with default data
    """
    username = await auth_client.get_user(request.headers['Authorization'])
    path = Path.validate_path(username, request.match_info['path'])
    importer_type = request.match_info['importerType']
    return web.json_response(await translate_for_importer(importer_type, path))


@routes.post('/upload')
async def upload_files_chunked(request: web.Request):
    """
    uploads a file into the staging area
    """
    token = request.headers['Authorization']
    username = await auth_client.get_user(token)
    await assert_globusid_exists(username, token)
    reader = await request.multipart()
    counter = 0
    if not request.has_body:
        raise web.HTTPBadRequest(text='must provide destPath and uploads in body')
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
    response = await some_metadata(
        path,
        desired_fields=['name', 'path', 'mtime', 'size', 'isFolder'],
        source='KBase upload'
    )
    return web.json_response([response])


@routes.post('/define-upa/{path:.+}')
async def define_UPA(request: web.Request):
    """
    creates an UPA as a field in the metadata file corresponding to the filepath given
    """
    username = await auth_client.get_user(request.headers['Authorization'])
    path = Path.validate_path(username, request.match_info['path'])
    if not os.path.exists(path.full_path or not os.path.isfile(path.full_path)):
        # TODO the security model here is to not care if someone wants to put in a false upa
        raise web.HTTPNotFound(text='no file found found on path {}'.format(path.user_path))
    if not request.has_body:
        raise web.HTTPBadRequest(text='must provide UPA field in body')
    body = await request.post()
    try:
        UPA = body['UPA']
    except KeyError as wrong_key:
        raise web.HTTPBadRequest(text='must provide UPA field in body')
    await add_upa(path, UPA)
    return web.Response(
        text='succesfully updated UPA {UPA} for file {path}'.format(UPA=UPA, path=path.user_path)
        )


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
        raise web.HTTPForbidden(text='cannot rename or move home directory')
    if is_globusid(path, username):
        raise web.HTTPForbidden(text='cannot rename or move protected file')
    if not request.has_body:
        raise web.HTTPBadRequest(text='must provide newPath field in body')
    body = await request.post()
    try:
        new_path = body['newPath']
    except KeyError as wrong_key:
        raise web.HTTPBadRequest(text='must provide newPath field in body')
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


@routes.patch('/decompress/{path:.+}')
async def decompress(request: web.Request):
    username = await auth_client.get_user(request.headers['Authorization'])
    path = Path.validate_path(username, request.match_info['path'])
    # make sure the file can be decompressed
    filename, file_extension = os.path.splitext(path.full_path)
    filename, upper_file_extension = os.path.splitext(filename)
    # TODO behavior when the unzip would overwrite something, what does it do, what should it do
    # 1 if we just don't let it do this its important to provide the rename feature,
    # 2 could try again after doign an automatic rename scheme (add nubmers to end)
    # 3 just overwrite and force
    destination = os.path.dirname(path.full_path)
    if (upper_file_extension == '.tar' and file_extension == '.gz') or file_extension == '.tgz':
        await run_command('tar', 'xzf', path.full_path, '-C', destination)
    elif upper_file_extension == '.tar' and (file_extension == '.bz' or file_extension == '.bz2'):
        await run_command('tar', 'xjf', path.full_path, '-C', destination)
    elif file_extension == '.zip' or file_extension == '.ZIP':
        await run_command('unzip', path.full_path, '-d', destination)
    elif file_extension == '.tar':
        await run_command('tar',  'xf', path.full_path, '-C', destination)
    elif file_extension == '.gz':
        await run_command('gzip', '-d', path.full_path)
    elif file_extension == '.bz2' or file_extension == 'bzip2':
        await run_command('bzip2', '-d', path.full_path)
    else:
        raise web.HTTPBadRequest(
            text='cannot decompress a {ext} file'.format(ext=file_extension))
    return web.Response(text='succesfully decompressed ' + path.user_path)


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
    DATA_DIR = config['staging_service']['DATA_DIR']
    META_DIR = config['staging_service']['META_DIR']
    if DATA_DIR.startswith('.'):
        DATA_DIR = os.path.normpath(os.path.join(os.getcwd(), DATA_DIR))
    if META_DIR.startswith('.'):
        META_DIR = os.path.normpath(os.path.join(os.getcwd(), META_DIR))
    Path._DATA_DIR = DATA_DIR
    Path._META_DIR = META_DIR
    global auth_client
    auth_client = KBaseAuth2(config['staging_service']['AUTH_URL'])
    return app
