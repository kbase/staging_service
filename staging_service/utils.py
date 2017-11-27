import asyncio
from aiohttp.web import HTTPInternalServerError
import os


async def run_command(*args):
    """Run command in subprocess
    Example from:
        http://asyncio.readthedocs.io/en/latest/subprocess.html
    """
    # Create subprocess
    process = await asyncio.create_subprocess_exec(
        *args,
        # stdout must a pipe to be accessible as process.stdout
        stdout=asyncio.subprocess.PIPE)

    # Status
    # print('Started:', args, '(pid = ' + str(process.pid) + ')')

    # Wait for the subprocess to finish
    stdout, stderr = await process.communicate()

    # Progress
    if process.returncode == 0:
        return stdout.decode().strip()
    else:
        raise HTTPInternalServerError(text='command {cmd} failed'.format(cmd=' '.join(args)))
        # TODO this should give better information on what went wrong in the process


class Path(object):
    _META_DIR = None  # expects to be set by config
    _DATA_DIR = None  # expects to be set by config
    __slots__ = ['full_path', 'metadata_path', 'user_path', 'name']

    def __init__(self, full_path, metadata_path, user_path, name):
        self.full_path = full_path
        self.metadata_path = metadata_path
        self.user_path = user_path
        self.name = name

    @staticmethod
    def validate_path(username: str, path: str=''):
        """
        @returns a path object based on path that must start with username
        throws an exeception for an invalid path or username
        starts path at first occurance of username"""
        if len(path) > 0:
            path = os.path.normpath(path)
            path = path.replace('..', '/')
            path = os.path.normpath(path)
            if path == '.':
                path = ''
            while path.startswith('/'):
                path = path[1:]
        user_path = os.path.join(username, path)
        full_path = os.path.join(Path._DATA_DIR, user_path)
        metadata_path = os.path.join(Path._META_DIR, user_path)
        name = os.path.basename(path)
        return Path(full_path, metadata_path, user_path, name)

    @staticmethod
    def from_full_path(full_path: str):
        user_path = full_path[len(Path._DATA_DIR):]
        metadata_path = os.path.join(Path._META_DIR, user_path)
        name = os.path.basename(full_path)
        return Path(full_path, metadata_path, user_path, name)
