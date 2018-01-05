from json import JSONDecoder, JSONEncoder
import aiofiles
from .utils import run_command, Path
import os
from aiohttp import web
import hashlib

decoder = JSONDecoder()
encoder = JSONEncoder()


async def stat_data(path: Path) -> dict:
    """
    only call this on a validated full path
    """
    file_stats = os.stat(path.full_path)
    isFolder = os.path.isdir(path.full_path)
    return {
        'name': path.name,
        'path': path.user_path,
        'mtime': int(file_stats.st_mtime*1000),  # given in seconds, want ms
        'size': file_stats.st_size,
        'isFolder': isFolder
    }

async def _generate_metadata(path: Path, source: str):
    os.makedirs(os.path.dirname(path.metadata_path), exist_ok=True)
    if os.path.exists(path.metadata_path):
        async with aiofiles.open(path.metadata_path, mode='r') as extant:
            data = await extant.read()
            data = decoder.decode(data)
    else:
        data = {}
    # first ouptut of md5sum is the checksum
    data['source'] = source
    try:
        md5 = hashlib.md5(open(path.full_path, 'rb').read()).hexdigest()
    except:
        md5 = 'n/a'

    data['md5'] = md5.split()[0]
    # first output of wc is the count
    lineCount = await run_command('wc', '-l', path.full_path)
    data['lineCount'] = lineCount.split()[0]
    try:  # all things that expect a text file to decode output should be in this block
        data['head'] = await run_command('head', '-10', path.full_path)
        data['tail'] = await run_command('tail', '-10', path.full_path)
    except UnicodeDecodeError as not_text_file:
        data['head'] = 'not text file'
        data['tail'] = 'not text file'
    async with aiofiles.open(path.metadata_path, mode='w') as f:
        await f.writelines(encoder.encode(data))
    return data


async def add_upa(path: Path, UPA: str):
    if os.path.exists(path.metadata_path):
        async with aiofiles.open(path.metadata_path, mode='r') as extant:
            data = await extant.read()
            data = decoder.decode(data)
    else:
        data = await _generate_metadata(path)  # TODO performance optimization
    data['UPA'] = UPA
    os.makedirs(os.path.dirname(path.metadata_path), exist_ok=True)
    async with aiofiles.open(path.metadata_path, mode='w') as update:
        await update.writelines(encoder.encode(data))


def _determine_source(path: Path):
    """
    tries to determine the source of a file for which the source is unknown
    currently this works for JGI imported files only
    """
    jgi_path = path.jgi_metadata
    if os.path.exists(jgi_path) and os.path.isfile(jgi_path):
        return 'JGI import'
    else:
        return 'Unknown'


async def _only_source(path: Path):
    if os.path.exists(path.metadata_path):
        async with aiofiles.open(path.metadata_path, mode='r') as extant:
            data = await extant.read()
            data = decoder.decode(data)
    else:
        data = {}
    if 'source' in data:
        return data['source']
    else:
        data['source'] = _determine_source(path)
    os.makedirs(os.path.dirname(path.metadata_path), exist_ok=True)
    async with aiofiles.open(path.metadata_path, mode='w') as update:
        await update.writelines(encoder.encode(data))
    return data['source']


async def dir_info(path: Path, show_hidden: bool, query: str = '', recurse=True) -> list:
    """
    only call this on a validated full path
    """
    response = []
    for entry in os.scandir(path.full_path):
        specific_path = Path.from_full_path(entry.path)
        if not show_hidden and entry.name.startswith('.'):
            continue
        if entry.is_dir():
            if query == '' or specific_path.user_path.find(query) != -1:
                response.append(await stat_data(specific_path))
            if recurse:
                response.extend(await dir_info(specific_path, show_hidden, query, recurse))
        if entry.is_file():
            if query == '' or specific_path.user_path.find(query) != -1:
                data = await stat_data(specific_path)
                data['source'] = await _only_source(specific_path)
                response.append(data)
    return response


async def some_metadata(path: Path, desired_fields=False, source=None):
    """
    if desired fields isn't given as a list all fields will be returned
    assumes full_path is valid path to a file
    valid fields for desired_fields are:
    md5, lineCount, head, tail, name, path, mtime, size, isFolder, UPA
    """
    file_stats = await stat_data(path)
    if file_stats['isFolder']:
        return file_stats
    if ((not os.path.exists(path.metadata_path)) or
       (os.stat(path.metadata_path).st_mtime < file_stats['mtime']/1000)):
        # if metadata  does not exist or older than file: regenerate
        if source is None:
            source = _determine_source(path)
        data = await _generate_metadata(path, source)
    else:  # metadata already exists and is up to date
        async with aiofiles.open(path.metadata_path, mode='r') as f:
            # make metadata fields local variables
            data = await f.read()
            data = decoder.decode(data)
        # due to legacy code, some file has corrupted metadata file
        expected_keys = ['source', 'md5', 'lineCount', 'head', 'tail']
        if set(expected_keys) > set(data.keys()):
            if source is None:
                source = _determine_source(path)
            data = await _generate_metadata(path, source)
    data = {**data, **file_stats}
    if not desired_fields:
        return data
    result = {}
    for key in desired_fields:
        try:
            result[key] = data[key]
        except KeyError as no_data:
            raise web.HTTPBadRequest(text='no data exists for key {key}'.format(key=no_data.args))  # TODO check this exception message
    return result
