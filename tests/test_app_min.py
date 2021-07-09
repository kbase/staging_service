import asyncio
import os
import shutil

from aiohttp import test_utils

import gdi.app_min as app

DATA_DIR = os.path.normpath(os.path.join(os.getcwd(), './data/bulk/'))

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


class FileUtil:
    def __init__(self, base_dir=DATA_DIR):
        self.base_dir = base_dir

    def __enter__(self):
        os.makedirs(self.base_dir, exist_ok=True)
        shutil.rmtree(self.base_dir)
        os.makedirs(self.base_dir, exist_ok=False)
        return self

    def __exit__(self, *args):
        shutil.rmtree(self.base_dir)

    def make_file(self, path, contents):
        path = os.path.join(self.base_dir, path)
        with open(path, encoding="utf-8", mode="w") as f:
            f.write(contents)
        return path

    def make_dir(self, path):
        path = os.path.join(self.base_dir, path)
        os.makedirs(path, exist_ok=True)
        return path

    def remove_dir(self, path):
        shutil.rmtree(path)


async def test_upload():
    async with AppClient() as cli:

        with FileUtil() as fs:
            d = fs.make_dir(os.path.join("test"))
            await do_thing(fs, cli, "test_file_1")
            await do_thing(fs, cli, "test_file_2")

async def do_thing(fs, cli, filename):
    f = fs.make_file(os.path.join("test", filename), "testtext")

    files = {"uploads": open(f, "rb")}

    res = await cli.post(
        os.path.join("upload"), headers={"Authorization": ""}, data=files
    )

    print(f'\n*** res for {filename} ***')
    t = await(res.text())
    print(t)
    print(f"***")
    assert res.status == 200
