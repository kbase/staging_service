import configparser
import os

import aiofiles
import aiohttp

from .utils import StagingPath


def _get_authme_url():
    config = configparser.ConfigParser()
    config.read(os.environ["KB_DEPLOYMENT_CONFIG"])
    auth2_url = config["staging_service"]["AUTH_URL"]

    auth2_me_url = auth2_url.split("services")[0] + "services/auth/api/V2/me"

    return auth2_me_url


async def _get_globus_ids(token):
    if not token:
        raise aiohttp.web.HTTPBadRequest(text="must supply token")

    async with aiohttp.ClientSession() as session:
        auth2_me_url = _get_authme_url()
        async with session.get(auth2_me_url, headers={"Authorization": token}) as resp:
            ret = await resp.json()
            if not resp.reason == "OK":
                raise aiohttp.web.HTTPUnauthorized(
                    text="Error connecting to auth service: {} {}\n{}".format(
                        ret["error"]["httpcode"], resp.reason, ret["error"]["message"]
                    )
                )
    return list(
        map(
            lambda x: x["provusername"],
            filter(lambda x: x["provider"] == "Globus", ret["idents"]),
        )
    )


def _globus_id_path(username: str):
    return StagingPath.validate_path(username, ".globus_id")


def is_globusid(path: StagingPath, username: str):
    return path.full_path == _globus_id_path(username)


async def assert_globusid_exists(username, token):
    """ensures that a globus id exists if there is a valid one for user"""

    path = _globus_id_path(username)

    # Ensure the path to the globus file exists. In a deployment, this is the
    # user's staging directory.
    os.makedirs(os.path.dirname(path.full_path), exist_ok=True)

    # Create the globus
    if not os.path.exists(path.full_path) or os.stat(path.full_path).st_size == 0:
        globus_ids = await _get_globus_ids(token)
        if len(globus_ids) == 0:
            return

        # TODO in the future this should support writing multiple lines
        # such as the commented code below, for multiple linked accounts
        # text = '\n'.join(globus_ids)
        text = globus_ids[0]
        async with aiofiles.open(path.full_path, mode="w") as globus_file:
            await globus_file.write(text)
