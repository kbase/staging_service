from json import JSONDecoder, JSONEncoder
import aiofiles
import asyncio

import os

META_DIR = './data/metadata/'  # TODO configify
DATA_DIR = './data/bulk/'
decoder = JSONDecoder()
encoder = JSONEncoder()


async def stat_data(filename: str, full_path: str, isFolder=False) -> dict:
    file_stats = os.stat(full_path)
    return {
        'name': filename,
        'path': full_path,
        'mtime': int(file_stats.st_mtime*1000),  # given in seconds, want ms
        'size': file_stats.st_size,
        'isFolder': isFolder
    }


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
        # TODO
        pass


async def generate_metadata(filepath: str, metadata_path: str):
    os.makedirs(os.path.dirname(metadata_path), exist_ok=True)
    data = {}
    # first ouptut of md5sum is the checksum
    md5 = await run_command('md5sum', filepath)
    data['md5'] = md5.split()[0]
    # first output of wc is the count
    lineCount = await run_command('wc', '-l', filepath)
    data['lineCount'] = lineCount.split()[0]
    data['head'] = await run_command('head', '-10', filepath)
    data['tail'] = await run_command('tail', '-10', filepath)
    async with aiofiles.open(metadata_path, mode='w') as f:
        await f.writelines(encoder.encode(data))
    return data


async def some_metadata(filename: str, full_path: str, desired_fields: list):
    """
    assumes full_path is valid path to a file
    valid fields for desired_fields are:
    md5, lineCount, head, tail, name, path, mtime, size, isFolder
    """
    user_path = full_path[len(DATA_DIR):]
    if os.path.isdir(full_path):
        return {'error': 'cannot determine metadata for directory'}
    file_stats = await stat_data(filename, full_path)
    metadata_path = os.path.join(META_DIR, user_path+'.json')  # TODO this is a shitty way to store all the metadata
    if not os.path.exists(metadata_path):
        data = await generate_metadata(full_path, metadata_path)
    elif os.stat(metadata_path).st_mtime < file_stats['mtime']/1000:  # metadata is older than file
        data = await generate_metadata(full_path, metadata_path)
    else:  # metadata already exists and is up to date  
        async with aiofiles.open(metadata_path, mode='r') as f:
            # make metadata fields local variables
            data = await f.read()
            data = decoder.decode(data)
    data = {**data, **file_stats}
    result = {}
    for key in desired_fields:
        try:
            result[key] = data[key]  
        except KeyError as no_data:
            result[key] = 'error: data not found'  # TODO is this a good way to handle this?
    return result
