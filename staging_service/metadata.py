import hashlib
import os
import unicodedata
from difflib import SequenceMatcher
from json import JSONDecoder, JSONEncoder

import aiofiles
from aiohttp import web

from .utils import StagingPath

decoder = JSONDecoder()
encoder = JSONEncoder()

READ_BUFFER_SIZE = 1 * 1000 * 1000
FILE_SNIPPET_SIZE = 1024

# Set as the value for snippets for a non-text file
NOT_TEXT_FILE_VALUE = "not a text file"

SOURCE_JGI_IMPORT = "JGI import"
SOURCE_UNKNOWN = "Unknown"


async def stat_data(path: StagingPath) -> dict:
    """
    Returns our version of file stats.

    only call this on a validated full path
    """
    file_stats = os.stat(path.full_path)
    is_folder = os.path.isdir(path.full_path)
    return {
        "name": path.name,
        "path": path.user_path,
        "mtime": int(file_stats.st_mtime * 1000),  # given in seconds, want ms
        "size": file_stats.st_size,
        "isFolder": is_folder,
    }


def _file_read_from_tail(file_path):
    """
    Returns a snippet of text from the end of the given file.

    The snippet will be either FILE_SNIPPET_SIZE or the
    entire file if it is smaller than that.

    If the file is not proper utf-8 encoded, an error message
    will be returned instead.
    """
    upper_bound = min(FILE_SNIPPET_SIZE, os.stat(file_path).st_size)
    with open(file_path, "r", encoding="utf-8") as file:
        file.seek(0, os.SEEK_END)
        file.seek(file.tell() - upper_bound, os.SEEK_SET)
        try:
            return file.read()
        except UnicodeError:
            # Note that this string propagates all the way to the ui.
            return NOT_TEXT_FILE_VALUE


def _file_read_from_head(file_path):
    """
    Returns a snippet of text from the beginning of the given file.

    The snippet will be either FILE_SNIPPET_SIZE or the
    entire file if it is smaller than that.

    If the file is not proper utf-8 encoded, an error message
    will be returned instead.
    """
    with open(file_path, "r", encoding="utf-8") as file:
        try:
            return file.read(FILE_SNIPPET_SIZE)
        except UnicodeError:
            # Note that this string propagates all the way to the ui.
            return NOT_TEXT_FILE_VALUE


async def _read_metadata(metadata_path: str):
    """
    Reads the file at the provided path, and decodes to JSON.
    """
    async with aiofiles.open(metadata_path, mode="r", encoding="utf-8") as extant:
        data = await extant.read()
        return decoder.decode(data)


async def _get_metadata(metadata_path: str):
    """
    Gets the file metadata from the file system or, if it doesn't exist,
    return an empty dict.
    """
    try:
        return await _read_metadata(metadata_path)
    except FileNotFoundError:
        os.makedirs(os.path.dirname(metadata_path), exist_ok=True)
        return {}


def is_text_string(bytes_to_check):
    """
    Determines if the provided bytes is indeed a text string.

    It is considered a valid string if it is utf-8 encoded and
    does not contain control characters.

    This determination is for the purpose of determining whether to
    generate text snippets and report lines of text.
    """
    try:
        # If it decodes, it is indeed Unicode.
        decoded = bytes_to_check.decode("utf-8")

        # But it may not be text, as control characters may be
        # in there, and they are unlikely to be part of
        # readable text, which is what we are after here, as we
        # use this to enable line counting and snippets.
        # We allow TAB (9), LF (10), CR (13) for obvious reasons.
        for character in decoded:
            if unicodedata.category(character) == "Cc" and ord(character) not in [
                9,
                10,
                13,
            ]:
                return False

        return True
    except UnicodeError:
        return False


async def _generate_metadata(path: StagingPath, source: str = None):
    """
    Generates a metadata file for the associated data file.

    Note that it generates it unconditionally. For conditional generation, see _ensure_metadata.
    """
    # Open metadatafile if it exists, otherwise create an
    # empty dict and ensure there is a writable directory for it
    # to be saved to.
    existing_metadata = await _get_metadata(path.metadata_path)

    additional_metadata = {}

    # We record the modification time for the file, in milliseconds, in order
    # to be able to determine if it has changed since the metadata was last
    # generated.
    file_stats = os.stat(path.full_path)
    additional_metadata["mtime"] = int(file_stats.st_mtime * 1000)

    # If source is missing (why woudld that be?), supply it with the one
    # provided, or attempt to determine it.
    if "source" not in existing_metadata and source is None:
        source = _determine_source(path)
        additional_metadata["source"] = source

    metadata = existing_metadata | additional_metadata

    # We want to know, roughly, if this is a text file or not ("binary");
    # setting to true initially is just part of the logic in the loop below.
    is_text = True

    # A word on counting lines. We simply count line endings. With a catch.
    # The final "line" may be of two forms. Either as counted here, with the
    # last line ending being at the very end of the file, or the last bytes
    # after the last line ending if the file ends without a terminal line ending.
    # The latter adds, unfortunately, extra code and complexity.
    line_count = 0

    # Keeping the previous chunk of bytes read from the file is necessary for accurate
    # line counting.
    last_chunk_read = None
    chunk_count = 0

    md5 = hashlib.md5()  # NOSONAR
    async with aiofiles.open(path.full_path, "rb") as fin:
        while True:
            chunk = await fin.read(READ_BUFFER_SIZE)

            # If attempt to read past end of file, a 0-length bytes is returned
            if len(chunk) == 0:
                break

            last_chunk_read = chunk
            chunk_count += 1
            md5.update(chunk)

            # We use the first chunk to determine if the file is valid utf-8 text.
            # The first chunk is 1MB, so this should be safe.
            if chunk_count == 1:
                is_text = is_text_string(chunk)

            if is_text:
                line_count += chunk.count(b"\n")

    #
    # If the last chunk does not end in a newline (LF), then it has a last line
    # which is terminated by the end of the file.
    #
    if last_chunk_read is not None and last_chunk_read[-1] != ord(b"\n"):
        line_count += 1

    metadata["lineCount"] = line_count if is_text else None

    metadata["md5"] = md5.hexdigest()

    metadata["head"] = (
        _file_read_from_head(path.full_path) if is_text else NOT_TEXT_FILE_VALUE
    )
    metadata["tail"] = (
        _file_read_from_tail(path.full_path) if is_text else NOT_TEXT_FILE_VALUE
    )

    # Save metadata file
    await _save_metadata(path, metadata)

    return metadata


async def _save_metadata(path: StagingPath, metadata: dict):
    """
    Saves the given metadata dictionary into the metadata file associated with the given path
    """
    async with aiofiles.open(path.metadata_path, mode="w") as f:
        await f.writelines(encoder.encode(metadata))


async def _update_metadata(path: StagingPath, additional_metadata: dict) -> dict:
    """
    Updates the metadata indicated by the path with the additional metadata
    provided.

    Assumes the metadata file exists, so it should always be called after
    _ensure_metadata.
    """
    metadata = await _read_metadata(path.metadata_path)

    new_metdata = metadata | additional_metadata

    await _save_metadata(path, new_metdata)

    return new_metdata


async def add_upa(path: StagingPath, upa: str):
    """
    Adds the provided UPA to the metadata for the given path.

    If the metadata does not yet exist, the metadata is generated.
    """
    await _ensure_metadata(path)
    await _update_metadata(path, {"UPA": upa})


def _determine_source(path: StagingPath):
    """
    tries to determine the source of a file for which the source is unknown
    currently this works for JGI imported files only
    """
    jgi_path = path.jgi_metadata
    if os.path.exists(jgi_path) and os.path.isfile(jgi_path):
        return SOURCE_JGI_IMPORT
    else:
        return SOURCE_UNKNOWN


async def dir_info(
    path: StagingPath, show_hidden: bool, query: str = "", recurse=True
) -> list:
    """
    Returns a directory listing of the given path.

    If a query is provided, only files containing it will be included.
    If show_hidden is True, any files with a "." prefix ("hidden files"), will
    be included, otherwise they are omitted
    If recurse is True, all subdirectories will be included.

    Only call this on a validated full path.
    """
    response = []
    for entry in os.scandir(path.full_path):
        specific_path = StagingPath.from_full_path(entry.path)
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
        elif entry.is_file():
            if query == "" or specific_path.user_path.find(query) != -1:
                metadata, file_stats = await _ensure_metadata(specific_path)
                file_stats["source"] = metadata["source"]
                response.append(file_stats)

    return response


async def similar(file_name, comparing_file_name, similarity_cut_off):
    """
    return true if file_name and comparing_file_name have higher similarity_cut_off
    """

    matcher = SequenceMatcher(None, file_name, comparing_file_name)

    return matcher.ratio() >= similarity_cut_off


async def _ensure_metadata(path: StagingPath, source: str = None):
    """
    Returns metdata if found, otherwise generates and returns it for the given file
    """
    file_stats = await stat_data(path)

    if os.path.exists(path.metadata_path):
        metadata = await _read_metadata(path.metadata_path)

        #
        # These are required properties of the metadata, so if any are missing,
        # due to corrupted metadata, old metadata generated during development,
        # or due to updates in the metadata format, this ensures that we trigger
        # a metadata rebuild.
        #
        built_in_keys = set(["source", "md5", "lineCount", "head", "tail", "mtime"])

        #
        # Note that we are checking if the built in keys are included in the metadata,
        # not that they are the complete set of metadata (although they may be).
        #
        if set(built_in_keys) <= set(metadata.keys()):
            #
            # This is why we store the modification time of the file. If the
            # file has been changed (as measured by the modification time), we
            # regenerate the metadata.
            #
            if metadata["mtime"] == file_stats["mtime"]:
                return metadata, file_stats

    metadata = await _generate_metadata(path, source)

    return metadata, file_stats


async def some_metadata(path: StagingPath, desired_fields=False, source=None):
    """
    Returns metadata with file stats merged, optionally filtered by a set of
    desired fields.

    If the desired fields are not provided, all fields will be returned.
    Valid fields for desired_fields are:
        md5, lineCount, head, tail, source, name, path, mtime, size, isFolder, UPA

    Assumes full_path is valid path to a file
    """
    metadata, file_stats = await _ensure_metadata(path, source)

    data = metadata | file_stats

    if not desired_fields:
        return data

    result = {}
    for key in desired_fields:
        try:
            result[key] = data[key]
        except KeyError as no_data:
            raise web.HTTPBadRequest(text=f"no data exists for key {no_data.args}")

    return result
