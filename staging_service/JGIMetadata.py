from .utils import Path
from json import JSONDecoder
import aiofiles
import os
from aiohttp import web

decoder = JSONDecoder()


async def read_metadata_for(path: Path):
    if os.path.exists(path.jgi_metadata) and os.path.isfile(path.jgi_metadata):
        async with aiofiles.open(path.jgi_metadata, mode='r') as json:
            data = await json.read()
            return decoder.decode(data)
    else:
        raise web.HTTPNotFound(
            text='could not find associated JGI metadata file for {path}'.format(path.user_path))


async def translate_for_importer(importer: str, path: Path):
    # TODO this should contain logic for translating jgi metadata
    # into the fields the importer expects
    return await read_metadata_for(path)