import hashlib
import os
from difflib import SequenceMatcher
from json import JSONDecoder, JSONEncoder
from typing import Union

import aiofiles
from aiohttp import web

from .utils import Path

decoder = JSONDecoder()
encoder = JSONEncoder()


async def stat_data(path: Path) -> dict:
    """
    only call this on a validated full path
    """
    file_stats = os.stat(path.full_path)
    isFolder = os.path.isdir(path.full_path)
    return {
        "name": path.name,
        "path": path.user_path,
        "mtime": int(file_stats.st_mtime * 1000),  # given in seconds, want ms
        "size": file_stats.st_size,
        "isFolder": isFolder,
    }


def _file_read_from_tail(file_path):
    upper_bound = min(1024, os.stat(file_path).st_size)
    with open(file_path, "r", encoding="utf-8") as file:
        file.seek(0, os.SEEK_END)
        file.seek(file.tell() - upper_bound, os.SEEK_SET)
        return file.read()


def _file_read_from_head(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read(1024)


async def _generate_metadata(path: Path, source: Union[str, None]):
    os.makedirs(os.path.dirname(path.metadata_path), exist_ok=True)
    if os.path.exists(path.metadata_path):
        async with aiofiles.open(path.metadata_path, mode="r") as extant:
            data = await extant.read()
            data = decoder.decode(data)
    else:
        data = {}
    # first ouptut of md5sum is the checksum
    if source:
        data["source"] = source
    try:
        md5 = hashlib.md5(open(path.full_path, "rb").read()).hexdigest()
    except Exception:
        md5 = "n/a"

    data["md5"] = md5.split()[0]
    # first output of wc is the count
    data["lineCount"] = str(sum((1 for i in open(path.full_path, "rb"))))
    try:  # all things that expect a text file to decode output should be in this block
        data["head"] = _file_read_from_head(path.full_path)
        data["tail"] = _file_read_from_tail(path.full_path)
    except Exception:
        data["head"] = "not text file"
        data["tail"] = "not text file"
    async with aiofiles.open(path.metadata_path, mode="w") as f:
        await f.writelines(encoder.encode(data))
    return data


async def add_upa(path: Path, UPA: str):
    if os.path.exists(path.metadata_path):
        async with aiofiles.open(path.metadata_path, mode="r") as extant:
            data = await extant.read()
            data = decoder.decode(data)
    else:
        data = await _generate_metadata(path, None)  # TODO performance optimization
    data["UPA"] = UPA
    os.makedirs(os.path.dirname(path.metadata_path), exist_ok=True)
    async with aiofiles.open(path.metadata_path, mode="w") as update:
        await update.writelines(encoder.encode(data))


def _determine_source(path: Path):
    """
    tries to determine the source of a file for which the source is unknown
    currently this works for JGI imported files only
    """
    jgi_path = path.jgi_metadata
    if os.path.exists(jgi_path) and os.path.isfile(jgi_path):
        return "JGI import"
    else:
        return "Unknown"


async def _only_source(path: Path):
    if os.path.exists(path.metadata_path):
        async with aiofiles.open(path.metadata_path, mode="r") as extant:
            try:
                data = await extant.read()
                data = decoder.decode(data)
            except Exception:
                data = {}
    else:
        data = {}
    if "source" in data:
        return data["source"]
    else:
        data["source"] = _determine_source(path)
    os.makedirs(os.path.dirname(path.metadata_path), exist_ok=True)
    async with aiofiles.open(path.metadata_path, mode="w") as update:
        await update.writelines(encoder.encode(data))
    return data["source"]


async def dir_info(
    path: Path, show_hidden: bool, query: str = "", recurse=True
) -> list:
    """
    only call this on a validated full path
    """
    response = []
    for entry in os.scandir(path.full_path):
        specific_path = Path.from_full_path(entry.path)
        # maybe should never show the special .globus_id file ever?
        # or moving it somewhere outside the user directory would be better
        if not show_hidden and entry.name.startswith("."):
            continue
        if entry.is_dir():
            if query == "" or specific_path.user_path.find(query) != -1:
                response.append(await stat_data(specific_path))
            if recurse:
                response.extend(
                    await dir_info(specific_path, show_hidden, query, recurse)
                )
        if entry.is_file():
            if query == "" or specific_path.user_path.find(query) != -1:
                data = await stat_data(specific_path)
                data["source"] = await _only_source(specific_path)
                response.append(data)
    return response


async def similar(file_name, comparing_file_name, similarity_cut_off):
    """
    return true if file_name and comparing_file_name have higher similarity_cut_off
    """

    matcher = SequenceMatcher(None, file_name, comparing_file_name)

    return matcher.ratio() >= similarity_cut_off


async def some_metadata(path: Path, desired_fields=False, source=None):
    """
    if desired fields isn't given as a list all fields will be returned
    assumes full_path is valid path to a file
    valid fields for desired_fields are:
    md5, lineCount, head, tail, name, path, mtime, size, isFolder, UPA
    """
    file_stats = await stat_data(path)
    if file_stats["isFolder"]:
        return file_stats
    if (not os.path.exists(path.metadata_path)) or (
        os.stat(path.metadata_path).st_mtime < file_stats["mtime"] / 1000
    ):
        # if metadata  does not exist or older than file: regenerate
        if source is None:  # TODO BUGFIX this will overwrite any source in the file
            source = _determine_source(path)
        data = await _generate_metadata(path, source)
    else:  # metadata already exists and is up to date
        async with aiofiles.open(path.metadata_path, mode="r") as f:
            # make metadata fields local variables
            data = await f.read()
            data = decoder.decode(data)
        # due to legacy code, some file has corrupted metadata file
        # Also if a file is listed or checked for existence before the upload completes
        # this code block will be triggered
        expected_keys = ["source", "md5", "lineCount", "head", "tail"]
        if not set(expected_keys) <= set(data.keys()):
            if source is None and "source" not in data:
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
            raise web.HTTPBadRequest(
                text=f"no data exists for key {no_data.args}"
            )  # TODO check this exception message
    return result
