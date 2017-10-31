import asyncio
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
        raise ChildProcessError()


class Path(object):
    _META_DIR = './data/metadata/'  # TODO configify
    _DATA_DIR = './data/bulk/'
    __slots__ = ['full_path', 'metadata_path', 'user_path']

    def __init__(self, full_path, metadata_path, user_path):
        self.full_path = full_path
        self.metadata_path = metadata_path
        self.user_path = user_path
        
    @staticmethod
    def validate_path(username: str, path: str):
        """
        @returns a path object based on path that must start with username
        throws an exeception for an invalid path or username
        starts path at first occurance of username"""
        path = os.path.normpath(path)
        start = path.find(username)
        if start == -1:
            raise ValueError('username not in path')
        user_path = path[start:]
        full_path = os.path.join(Path._DATA_DIR, user_path)
        metadata_path = os.path.join(Path._META_DIR, user_path)
        return Path(full_path, metadata_path, user_path)