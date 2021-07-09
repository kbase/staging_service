import asyncio
import os
import shutil

from aiohttp import test_utils

import gdi.app_min as app

class AppClient:
    def __init__(self):
        self.server = test_utils.TestServer(app.app_factory())

    async def __aenter__(self):
        await self.server.start_server(loop=asyncio.get_event_loop())
        self.client = test_utils.TestClient(self.server, loop=asyncio.get_event_loop())
        return self.client

    async def __aexit__(self, *args):
        await self.server.close()
        await self.client.close()


async def test_upload():
    testdir = os.path.normpath(os.path.join(os.getcwd(), './temptest/'))
    os.makedirs(testdir, exist_ok=True)
    async with AppClient() as cli:
        await _do_thing(cli, testdir, "test_file_1")
        await _do_thing(cli, testdir, "test_file_2")


async def _do_thing(cli, testdir, filename):
    path = os.path.join(testdir, filename)
    with open(path, encoding="utf-8", mode="w") as f:
        f.write("testtext")

    files = {"uploads": open(path, "rb")}

    res = await cli.post(
        os.path.join("upload"), headers={"Authorization": ""}, data=files
    )

    print(f'\n*** res for {filename} ***')
    print(await(res.text()))
    print(f"***")
    assert res.status == 200
