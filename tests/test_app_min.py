import asyncio
import os
import shutil

from aiohttp import test_utils

import staging_service.app_min as app

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
    txt = "testing text\n"
    username = "testuser"
    async with AppClient() as cli:

        with FileUtil() as fs:
            d = fs.make_dir(os.path.join(username, "test"))
            f = fs.make_file(os.path.join(username, "test", "test_file_1"), txt)

            files = {"uploads": open(f, "rb")}

            res2 = await cli.post(
                os.path.join("upload"), headers={"Authorization": ""}, data=files
            )

            print(res2)
            assert res2.status == 200

            # test upload file with leading .
            f3 = fs.make_file(os.path.join(username, "test", "test_file_2"), txt)

            files = {"uploads": open(f3, "rb")}

            res4 = await cli.post(
                os.path.join("upload"), headers={"Authorization": ""}, data=files
            )

            assert res4.status == 200
            print('****** res4 *****')
            print(res4)

            # test upload file with leading space
            f2 = fs.make_file(os.path.join(username, "test", " test_file_1"), txt)

            files = {"uploads": open(f2, "rb")}

            res3 = await cli.post(
                os.path.join("upload"), headers={"Authorization": ""}, data=files
            )

            assert res3.status == 403
            print('****** res3 *****')
            print(res3)

            f = fs.make_file(os.path.join(username, "test", "test_file_1"), txt)

            files = {"uploads": open(f, "rb")}

            res2 = await cli.post(
                os.path.join("upload"), headers={"Authorization": ""}, data=files
            )

            assert res2.status == 400
            print('****** res2 *****')
            print(res2)


            # test upload file with leading .
            f4 = fs.make_file(os.path.join(username, "test", "test_file_3"), txt)

            files = {"uploads": open(f4, "rb")}

            res5 = await cli.post(
                os.path.join("upload"), headers={"Authorization": ""}, data=files
            )

            assert res5.status == 403
            print('****** res5 *****')
            print(res5)

