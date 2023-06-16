import os
from json import JSONDecoder

import aiofiles
from aiohttp import web

from .utils import StagingPath

decoder = JSONDecoder()


async def read_metadata_for(path: StagingPath):
    if os.path.exists(path.jgi_metadata) and os.path.isfile(path.jgi_metadata):
        async with aiofiles.open(path.jgi_metadata, mode="r") as json:
            data = await json.read()
            return decoder.decode(data)
    else:
        raise web.HTTPNotFound(
            text="could not find associated JGI metadata file for {path}".format(
                path=path.user_path
            )
        )


