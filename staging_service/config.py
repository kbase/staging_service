import os

import configparser
from aiohttp import web

DEFAULT_UPLOAD_MAX_FILE_SIZE = 5 * 1000 * 1000 * 1000  # aka, 5GB
DEFAULT_UPLOAD_READ_CHUNK_SIZE = 1 * 1000 * 1000
UPLOAD_SAVE_STRATEGY_TEMP_THEN_COPY = "SAVE_STRATEGY_TEMP_THEN_COPY"
UPLOAD_SAVE_STRATEGY_SAVE_TO_DESTINATION = "SAVE_STRATEGY_SAVE_TO_DESTINATION"
DEFAULT_UPLOAD_SAVE_STRATEGY = UPLOAD_SAVE_STRATEGY_SAVE_TO_DESTINATION
# THe content length tweak represents the extra header overload for a request, which consists
# of the "fileDest" field and the header section of the upload file. 1K seems reasonable, and
# the whole business of capping the file size is approximate in any case.
# Casual testing shows 272 bytes for Chrome, without the actual destination file and file's
# filename, so 1728 bytes for the path and filename seems quite generous.
CONTENT_LENGTH_TWEAK = 2000


_CONFIG = None

def get_read_chunk_size() -> int:
    """
    Returns the configured chunk size for reading from the
    upload request stream.
    """
    chunk_size = os.environ.get("UPLOAD_READ_CHUNK_SIZE")
    if chunk_size is None:
        return DEFAULT_UPLOAD_READ_CHUNK_SIZE
    try:
        return int(chunk_size)
    except ValueError as ve:
        raise web.HTTPInternalServerError(
            text=f"Error parsing UPLOAD_READ_CHUNK_SIZE environment variable: {str(ve)}"
        )


def get_save_strategy() -> str:
    """
    Returns the "save strategy" as defined by the environment variable "UPLOAD_SAVE_STRATEGY",
    as well as the default value DEFAULT_SAVE_STRATEGY defined at the top of this file.
    """
    save_strategy = os.environ.get("UPLOAD_SAVE_STRATEGY")

    if save_strategy is None:
        return DEFAULT_UPLOAD_SAVE_STRATEGY

    if save_strategy not in [
        UPLOAD_SAVE_STRATEGY_TEMP_THEN_COPY,
        UPLOAD_SAVE_STRATEGY_SAVE_TO_DESTINATION,
    ]:
        raise web.HTTPInternalServerError(
            text=f"Unsupported save strategy in configuration: '{save_strategy}'"
        )

    return save_strategy


def get_max_file_size() -> int:
    max_file_size = os.environ.get("UPLOAD_MAX_FILE_SIZE")
    if max_file_size is None:
        return DEFAULT_UPLOAD_MAX_FILE_SIZE
    try:
        return int(max_file_size)
    except ValueError as ve:
        raise web.HTTPInternalServerError(
            text=f"Error parsing UPLOAD_MAX_FILE_SIZE environment variable: {str(ve)}"
        )


def get_max_content_length() -> int:
    max_file_size = get_max_file_size()
    return max_file_size + CONTENT_LENGTH_TWEAK


def get_config():
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = configparser.ConfigParser()
        _CONFIG.read(os.environ["KB_DEPLOYMENT_CONFIG"])
    return _CONFIG
