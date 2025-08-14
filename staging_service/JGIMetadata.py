import os
from json import JSONDecoder

import aiofiles
from aiohttp import web

from .utils import Path

decoder = JSONDecoder()


async def read_metadata_for(path: Path):
    if os.path.exists(path.jgi_metadata) and os.path.isfile(path.jgi_metadata):
        async with aiofiles.open(path.jgi_metadata, mode="r", encoding="utf-8") as json:
            data = await json.read()
            return decoder.decode(data)
    else:
        raise web.HTTPNotFound(
            text=f"could not find associated JGI metadata file for {path.user_path}"
        )
