from dataclasses import dataclass
import time
import traceback
import aiofiles
import asyncio
from watchfiles import Change, awatch
from pathlib import Path
import logging
import json
import shutil

from staging_service.config import StagingServiceConfig
from staging_service.kb_auth_client import InvalidTokenError, InvalidUserError, KBaseAuth
from staging_service.utils import Path as UserPath

LOGGER_NAME = "dts_file_watcher"
logger = logging.getLogger(LOGGER_NAME)

# TODO: move these hardcoded values to the StagingServiceConfig object and
# deployment config files.
# issue #238
TARGET_FILE_NAME = "manifest.json"
WAIT_INTERVAL_SEC = 1.0
STABLE_TIME = 2.0
WAIT_FOR_FILE_LIMIT = 5
WATCHFILES_POLL_DELAY_MS = 500
WATCHFILES_FORCE_POLLING = True
HEALTH_CHECK_TIMEOUT_SEC = 60


@dataclass
class DTSWatcherHealth:
    is_watching: bool
    last_heartbeat: int
    time_since_heartbeat: int
    is_healthy: bool
    watch_directory: str
    health_check_timeout: int


class DTSFileWatcher:
    """
    DTS File Watcher
    This uses watchfiles to monitor the given watch_dir for Data Transfer Service (DTS) manifest files.
    When files are copied over from the DTS, they are expected to follow a few rules:
    1. They come to the watched directory in a subdirectory (generally a UUID name, but doesn't matter)
    2. The last file to appear is a "manifest.json" file which contains information about the files copied.
    3. The root object of the file includes a username key that denotes the username.

    When a manifest.json file is detected, the entire directory it is located in should be moved to
    the user's staging area.
    """

    def __init__(self, auth_client: KBaseAuth, config: StagingServiceConfig):
        self._auth_client = auth_client
        self._watch_dir = Path(config.dts_staging_dir)
        self._config = config
        # the watcher listens for this on each loop, and stops when it's set.
        self._stop_event = asyncio.Event()
        self._last_heartbeat = time.time()
        self._is_watching = False

    async def start_watching_for_files(self) -> None:
        """
        Starts up the process for watching for DTS files.
        This uses the async version of watchfiles. This expects to run forever unless the asyncio
        stop event is triggered (self._stop_event).

        Because of the nature of file io messages not playing consistently with Docker containers,
        this uses the file system polling version. That is, instead of listening for inotify events,
        it periodically asks for them from the operating system. This is definitely not the most
        performant way this can work, but given how deployments happen, it seems to be ok.
        If there are performance issues with the staging service, adjust the poll delay time.

        Errors that occur while parsing manifest files or trying to move them will be logged, but
        shouldn't raise an error.

        TODO: add a tracker for the file copying process with a service endpoint for monitoring
        See issue #237
        """
        if not self._watch_dir.exists():
            err_str = (
                f"Directory to watch: {self._watch_dir} does not exist. Not watching for DTS files."
            )
            logger.error(err_str)
            raise FileNotFoundError(err_str)

        logger.info(f"watching dir {self._watch_dir} for DTS manifest files.")
        self._is_watching = True
        self._last_heartbeat = time.time()

        async for changes in awatch(
            self._watch_dir,
            force_polling=WATCHFILES_FORCE_POLLING,
            poll_delay_ms=WATCHFILES_POLL_DELAY_MS,
            step=1,
            stop_event=self._stop_event,
            yield_on_timeout=True,
        ):
            # update heartbeat on loop iteration, including timeouts
            self._last_heartbeat = time.time()

            for change_type, change_file_path in changes:
                file_path = Path(change_file_path)
                # manifest file must be in a subdirectory to be detected
                if (
                    change_type == Change.added
                    and file_path.name == TARGET_FILE_NAME
                    and file_path.parent != self._watch_dir
                ):
                    logger.info(f"New DTS manifest file detected: {file_path}")
                    try:
                        await self._process_complete_manifest(file_path)
                    except json.JSONDecodeError as e:
                        logger.error(
                            f"File {file_path} does not appear to be JSON formatted: {str(e)}"
                        )
                    except (ValueError, RuntimeError, MoveDtsFilesError) as e:
                        logger.error(str(e))
                    except Exception as e:
                        # Not sure how else this can fail, but just in case...
                        logger.error(f"Unexpected error: {e}\n{traceback.format_exc()}")
        self._is_watching = False
        logger.info(
            f"Stop event triggered, no longer watching {self._watch_dir} for DTS manifest files."
        )

    def stop_watching_for_files(self) -> None:
        self._stop_event.set()

    def is_healthy(self) -> bool:
        """
        Check if the file watcher is healthy.
        Returns True if:
        1. The watcher is currently watching
        2. The last heartbeat was within the timeout period
        """
        return self._is_watching and time.time() - self._last_heartbeat <= HEALTH_CHECK_TIMEOUT_SEC

    def get_health_status(self) -> DTSWatcherHealth:
        return DTSWatcherHealth(
            self._is_watching,
            self._last_heartbeat,
            time.time() - self._last_heartbeat,
            self.is_healthy(),
            str(self._watch_dir),
            HEALTH_CHECK_TIMEOUT_SEC,
        )

    async def _process_complete_manifest(self, manifest_path: Path):
        """
        It's incredibly unlikely for a "file created" event to get caught by watchfiles
        and not have the file present. This, however, gives it a few seconds, if that
        edge case happens.
        """
        wait_cycle = 0
        while not manifest_path.exists() and wait_cycle < WAIT_FOR_FILE_LIMIT:
            logger.info(f"Waiting for manifest file at {manifest_path} to appear")
            await asyncio.sleep(WAIT_INTERVAL_SEC)
            wait_cycle += 1

        if not manifest_path.exists():
            raise RuntimeError(
                f"Manifest file {manifest_path} did not appear after {WAIT_FOR_FILE_LIMIT * WAIT_INTERVAL_SEC} seconds"
            )

        # Wait for the file size to stabilize for WAIT_INTERVAL_SEC
        cur_size = manifest_path.stat().st_size
        last_check = asyncio.get_event_loop().time()

        while True:
            await asyncio.sleep(WAIT_INTERVAL_SEC)
            new_size = manifest_path.stat().st_size
            now = asyncio.get_event_loop().time()

            if new_size != cur_size:
                cur_size = new_size
                last_check = now
            elif now - last_check >= STABLE_TIME:
                break
        username = await self._get_user_from_manifest(manifest_path)
        # If the user doesn't exist in KBase, fail.
        try:
            if not await self._auth_client.is_valid_user(username, self._config.auth_token):
                raise ValueError(
                    f"User {username} referenced in manifest file {manifest_path} does not exist."
                )
        except (InvalidTokenError, InvalidUserError) as e:
            raise RuntimeError(
                f"Auth service failure while looking up username {username} in manifest file {manifest_path}: {str(e)}"
            )
        # always move files from the root of the manifest path to a subdirectory for the
        # user matching the manifest path.
        # e.g. if the manifest is in /data/bulk/dts/some_transfer_uuid/manifest.json
        # and the username is "kbase_user" move all files in that directory to
        # DATA_DIR/kbase_user/some_transfer_uuid/
        user_path = UserPath.validate_path(username)
        dts_path_name = manifest_path.parent.name
        dest_path = Path(user_path.full_path) / dts_path_name
        if dest_path.exists:
            dest_path = self._make_unique_path(dest_path)
        return await self._move_dts_files(manifest_path.parent, dest_path)

    async def _get_user_from_manifest(self, manifest_path: Path) -> str:
        """
        Opens the manifest JSON file and extract the username, expected at the
        top level.
        Raises a ValueError if:
        * File does not exist.
        * File's JSON has no "username" field at the top level, or username is an empty string.
        * Username is not a valid KBase user id.
        Raises a JSONDecodeError if the file is not JSON, or is malformed.
        """
        async with aiofiles.open(manifest_path, "r") as manifest_infile:
            manifest = json.loads(await manifest_infile.read())
        if "username" not in manifest:
            raise ValueError(f"Manifest file {manifest_path} is missing the 'username' key.")
        username = manifest["username"]
        if username is None or username.strip() == "":
            raise ValueError(f"Username in manifest file {manifest_path} is not a valid string.")
        return username

    async def _move_dts_files(self, src_path: Path, dest_path: Path):
        logger.info(f"Moving files from {src_path} to {dest_path}")
        # TODO: copy with checksum before removing? Issue #235
        try:
            # Needs to be stuffed in a thread, or this will block the webapp
            return await asyncio.to_thread(shutil.move, src_path, dest_path)
        except Exception as e:
            raise MoveDtsFilesError(f"Unable to move DTS files from {src_path} to {dest_path}: {e}")

    def _make_unique_path(self, existing_path: Path) -> Path:
        """
        Makes a unique path from one that exists to avoid overwriting.
        I.e. if the path /foo/bar exists, this return /foo/bar-1
        If /foo/bar-1 exists, it returns /foo/bar-2, etc.
        """
        count = 1
        while existing_path.exists():
            suffix = f"-{count}"
            if str(existing_path).endswith(suffix):
                existing_path = Path(str(existing_path).rstrip(suffix))
                count += 1
                suffix = f"-{count}"
            existing_path = Path(str(existing_path) + suffix)
        return existing_path


class MoveDtsFilesError(Exception):
    """An error thrown when moving the DTS files fails."""
