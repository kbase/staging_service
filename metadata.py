from json import JSONDecoder, JSONEncoder
import os

META_DIR = './data/metadata'  # TODO configify
DATA_DIR = './data/bulk'


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
    data['md5'] = await run_command('md5sum', filepath).split()[0]
    # first output of wc is the count
    data['linecount'] = await run_command('wc', '-l', filepath).split()[0]
    data['head'] = await run_command('head', '-10', filepath)
    data['tail'] = await run_command('tail', '-10', filepath)
    async with aiofiles.open(metadata_path, mode='w') as f:
        await f.writelines(encoder.encode(data))


async def some_metadata(filename: str, user_path: str, desired_fields: list):
    full_path = os.path.join(DATA_DIR, user_path)
    metadata_path = os.path.join(META_DIR, user_path+'.json')  # TODO this is a shitty way to store all the metadata
    if not os.path.exists(metadata_path):
        await generate_metadata(full_path, metadata_path)
    elif os.stat(metadata_path).st_mtime < file_stats.st_mtime:  # metadata is older than file
        await generate_metadata(full_path, metadata_path)
    async with aiofiles.open(metadata_path, mode='r') as f:
        # make metadata fields local variables
        data = await f.read()
        data = decoder.decode(data)
    result
    for key in desired_fields:
        try:
            
        except expression as identifier:
            pass
    try:
        return {key: data[key] for key in desired_fields}
    except KeyError as no_data:
        # could automatically dispatch the right function to generate if needed (would want to turn comprehension into loop for this)