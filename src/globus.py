from utils import Path
import aiohttp
import aiofiles
import os

_AUTH2_ME_URL = 'https://ci.kbase.us/services/auth/api/V2/me'


async def _get_globus_ids(token):
    if not token:
        raise ValueError('Must supply token')
    async with aiohttp.ClientSession() as session:
        async with session.get(_AUTH2_ME_URL, headers={'Authorization': token}) as resp:
            ret = await resp.json()
            if not resp.reason == 'OK':
                try:
                    err = ret.json()
                except:
                    ret.raise_for_status()
                raise ValueError('Error connecting to auth service: {} {}\n{}'
                                 .format(ret['error']['httpcode'], resp.reason,
                                         err['error']['message']))
    return list(map(lambda x: x['provusername'],
                    filter(lambda x: x['provider'] == 'Globus',
                    ret['idents'])))


def _globus_id_path(username: str):
    return Path.validate_path(username, '.globus_id')


def is_globusid(path: Path, username: str):
    return path.full_path == _globus_id_path(username)


async def assert_globusid_exists(username, token):
    """ ensures that a globus id exists if there is a valid one for user"""
    path = _globus_id_path(username)
    # check to see if file exists or is empty
    if not os.path.exists(path.full_path) or os.stat(path.full_path).st_size == 0:
        globus_ids = await _get_globus_ids(token)
        if len(globus_ids) == 0:
            return
        # TODO in the future this should support writing multiple lines
        # such as the commented code below, for multiple linked accounts
        # text = '\n'.join(globus_ids)
        text = globus_ids[0]
        async with aiofiles.open(path.full_path, mode='w') as globus_file:
            await globus_file.writelines(text)
