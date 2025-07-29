import json
import os
import time
from typing import Callable, Tuple
import aiofiles
import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from staging_service.config import StagingServiceConfig
from staging_service.dts_file_watcher import (
    WAIT_FOR_FILE_LIMIT,
    WAIT_INTERVAL_SEC,
    DTSFileWatcher,
    LOGGER_NAME,
    DTSWatcherHealth,
    MoveDtsFilesError,
    HEALTH_CHECK_TIMEOUT_SEC,
)
from pathlib import Path
from watchfiles import Change
from staging_service.utils import Path as StagingPath

from staging_service.kb_auth_client import KBaseAuth
from tests.test_utils import bootstrap_config

CONFIG = bootstrap_config()
# TODO: remove when adding templated config files
TEST_TOKEN = os.environ.get("KBASE_TEST_TOKEN")
CONFIG.auth_token = TEST_TOKEN

CI_USERNAME = "narrativetest"
CI_USERNAME_NOT_FOUND = "not_a_real_user_name_please_never_make_this_real_omg"


@pytest.fixture(scope="function")
def config_tmp_path(tmp_path):
    """
    Monkeypatch file paths in the config to be rooted in tmp_path
    ONLY configures data_dir and dts_staging_dir
    """
    data_dir = CONFIG.data_dir
    dts_staging_dir = CONFIG.dts_staging_dir
    meta_dir = CONFIG.meta_dir
    CONFIG.data_dir = tmp_path / "data"
    CONFIG.data_dir.mkdir()
    CONFIG.dts_staging_dir = tmp_path / "dts"
    CONFIG.dts_staging_dir.mkdir()
    CONFIG.meta_dir = tmp_path / "metadata"
    CONFIG.meta_dir.mkdir()
    StagingPath._DATA_DIR = CONFIG.data_dir
    StagingPath._META_DIR = CONFIG.meta_dir
    yield CONFIG
    CONFIG.data_dir = data_dir
    CONFIG.dts_staging_dir = dts_staging_dir
    CONFIG.meta_dir = meta_dir
    StagingPath._DATA_DIR = None
    StagingPath._META_DIR = None


@pytest.fixture(scope="module")
async def auth_client():
    return await KBaseAuth.create(CONFIG.auth_url)


async def _run_watcher_once(watcher: DTSFileWatcher, wait_time: int = 0):
    """
    A convenience method that starts and stops the watcher at its first cycle.
    """
    task = asyncio.create_task(watcher.start_watching_for_files())
    await asyncio.sleep(wait_time)
    watcher.stop_watching_for_files()
    await task


def make_mocked_awatch(returned_events: list[Tuple[Change, str]]) -> Callable:
    """
    Don't actually watch the file system, but make an awatch that gets fed events
    to monitor, so we don't have to muck around with file io things as much.
    """

    async def fake_awatch(*args, **kwargs):
        yield returned_events

    return fake_awatch


async def test_dts_file_watcher_loop_runs_and_stops(config_tmp_path):
    watcher = DTSFileWatcher(None, config_tmp_path)

    task = asyncio.create_task(watcher.start_watching_for_files())
    await asyncio.sleep(1)  # give it time to enter the loop
    watcher.stop_watching_for_files()
    await asyncio.wait_for(task, timeout=2)
    assert task.done()


async def test_top_level_manifest_ignored(config_tmp_path):
    manifest_path = config_tmp_path.dts_staging_dir / "manifest.json"
    manifest_path.touch()

    watcher = DTSFileWatcher(None, config_tmp_path)
    watcher._process_complete_manifest = AsyncMock()

    with patch(
        "staging_service.dts_file_watcher.awatch",
        new=make_mocked_awatch([(Change.added, str(manifest_path))]),
    ):
        await _run_watcher_once(watcher)

    watcher._process_complete_manifest.assert_not_awaited()


async def test_manifest_found(config_tmp_path):
    manifest_dir = config_tmp_path.dts_staging_dir / "subdir"
    manifest_dir.mkdir()
    manifest_path = manifest_dir / "manifest.json"
    manifest_path.touch()

    watcher = DTSFileWatcher(None, config_tmp_path)
    # mocking here, test is focused on manifest detection
    watcher._process_complete_manifest = AsyncMock()

    with patch(
        "staging_service.dts_file_watcher.awatch",
        new=make_mocked_awatch([(Change.added, str(manifest_path))]),
    ):
        await _run_watcher_once(watcher)

    watcher._process_complete_manifest.assert_awaited()


async def test_dts_file_watcher_fail_no_dir():
    fake_dir = Path("/not/a/real/directory")
    config = bootstrap_config()
    config.dts_staging_dir = fake_dir
    watcher = DTSFileWatcher(None, config)
    with pytest.raises(FileNotFoundError, match="Not watching for DTS files"):
        await watcher.start_watching_for_files()


def make_manifest_file(config: StagingServiceConfig, manifest_text: str | None = None) -> Path:
    manifest_dir = config.dts_staging_dir / "fake_transfer"
    manifest_dir.mkdir()
    manifest_file = manifest_dir / "manifest.json"
    if manifest_text is not None:
        manifest_file.write_text(manifest_text)

    return manifest_file


async def run_manifest_fail_test(
    auth_client: KBaseAuth,
    config: StagingServiceConfig,
    manifest_path: Path,
    caplog,
    expected_err_log: str,
):
    """
    Assumes that config.dts_staging_dir is empty and can be freely written to.
    Should probably be a temp path.
    """
    # Setup dummy manifest file

    watcher = DTSFileWatcher(auth_client, config)
    with patch(
        "staging_service.dts_file_watcher.awatch",
        new=make_mocked_awatch([(Change.added, str(manifest_path))]),
    ):
        with caplog.at_level("ERROR", logger=LOGGER_NAME):
            await _run_watcher_once(watcher)

    assert expected_err_log in caplog.messages[0]


async def test_manifest_not_json(auth_client, config_tmp_path, caplog):
    manifest_path = make_manifest_file(config_tmp_path, "this is not json")

    await run_manifest_fail_test(
        auth_client,
        config_tmp_path,
        manifest_path,
        caplog,
        f"File {manifest_path} does not appear to be JSON formatted",
    )


@pytest.mark.parametrize("empty_user", [None, "  ", ""])
async def test_manifest_no_user(auth_client, config_tmp_path, caplog, empty_user):
    manifest_path = make_manifest_file(
        config_tmp_path, manifest_text=json.dumps({"username": empty_user})
    )

    await run_manifest_fail_test(
        auth_client,
        config_tmp_path,
        manifest_path,
        caplog,
        f"Username in manifest file {manifest_path} is not a valid string.",
    )


async def test_manifest_no_username_key(auth_client, config_tmp_path, caplog):
    manifest_path = make_manifest_file(config_tmp_path, manifest_text=json.dumps({"foo": "bar"}))

    await run_manifest_fail_test(
        auth_client,
        config_tmp_path,
        manifest_path,
        caplog,
        f"Manifest file {manifest_path} is missing the 'username' key.",
    )


async def test_manifest_not_found(auth_client, config_tmp_path, caplog):
    manifest_path = make_manifest_file(config_tmp_path)

    # TODO: update to config values
    await run_manifest_fail_test(
        auth_client,
        config_tmp_path,
        manifest_path,
        caplog,
        f"Manifest file {manifest_path} did not appear after {WAIT_FOR_FILE_LIMIT * WAIT_INTERVAL_SEC} seconds",
    )


async def test_user_not_found(config_tmp_path, caplog, auth_client):
    manifest_path = make_manifest_file(
        config_tmp_path, manifest_text=json.dumps({"username": CI_USERNAME_NOT_FOUND})
    )

    await run_manifest_fail_test(
        auth_client,
        config_tmp_path,
        manifest_path,
        caplog,
        f"User {CI_USERNAME_NOT_FOUND} referenced in manifest file {manifest_path} does not exist.",
    )


async def test_user_invalid_string(config_tmp_path, caplog, auth_client):
    illegal_user = "123__++??"
    manifest_path = make_manifest_file(
        config_tmp_path, manifest_text=json.dumps({"username": illegal_user})
    )

    await run_manifest_fail_test(
        auth_client,
        config_tmp_path,
        manifest_path,
        caplog,
        f"Auth service failure while looking up username {illegal_user} in manifest file {manifest_path}",
    )


async def test_move_dts_files_fail():
    src_path = Path("/this/path/does/not/exist")
    dest_path = Path("/this/path/also/does/not/exist")
    # kind of a hack to test it this way, but I'm not sure how to make the
    # shutil.move command fail through the watcher's usual code path.
    # By the time it gets to that point, both directories
    # should exist and be readable / writeable.
    # So I'm just testing the issue here and making sure it throws an Exception
    # properly.
    watcher = DTSFileWatcher(None, CONFIG)
    expected_err = f"Unable to move DTS files from {src_path} to {dest_path}"
    with pytest.raises(MoveDtsFilesError, match=expected_err):
        await watcher._move_dts_files(src_path, dest_path)


async def test_dts_watcher_end_to_end_success(config_tmp_path, caplog, auth_client):
    # put files in tmp_path/dts (use tmp_path as config for dts staging)
    # make another tmp_path/base for base dir, make config as such
    # use real username in CI
    # start watcher
    # test that move worked
    manifest_text = json.dumps({"username": CI_USERNAME})
    manifest_path = make_manifest_file(config_tmp_path, manifest_text=manifest_text)
    dts_dir = manifest_path.parent
    target_dir_name = dts_dir.name
    file_list = {"foo.fasta", "bar.fasta", "baz.zip"}
    for filename in file_list:
        (dts_dir / filename).touch()
        (dts_dir / filename).write_text(f"my name is {filename}")

    watcher = DTSFileWatcher(auth_client, config_tmp_path)
    with patch(
        "staging_service.dts_file_watcher.awatch",
        new=make_mocked_awatch([(Change.added, str(manifest_path))]),
    ):
        with caplog.at_level("INFO", logger=LOGGER_NAME):
            await _run_watcher_once(watcher, wait_time=5)

    target_dir = config_tmp_path.data_dir / CI_USERNAME / target_dir_name
    assert target_dir.exists()
    assert target_dir.is_dir()
    file_list.add("manifest.json")
    for item in target_dir.iterdir():
        if item.is_file():
            assert item.name in file_list
            async with aiofiles.open(item) as infile:
                test_data = await infile.read()
                if item.name == "manifest.json":
                    assert test_data == manifest_text
                else:
                    assert test_data == f"my name is {item.name}"


async def test_dts_watcher_end_to_end_duplicate_path(config_tmp_path, caplog, auth_client):
    # put files in tmp_path/dts (use tmp_path as config for dts staging)
    # make another tmp_path/base for base dir, make config as such
    # use real username in CI
    # start watcher
    # test that move worked
    manifest_text = json.dumps({"username": CI_USERNAME})
    manifest_path = make_manifest_file(config_tmp_path, manifest_text=manifest_text)
    dts_dir = manifest_path.parent
    target_dir_name = dts_dir.name
    target_dir = config_tmp_path.data_dir / CI_USERNAME / target_dir_name
    target_dir.mkdir(parents=True, exist_ok=True)  # make an existing dir. It can be empty.
    file_list = {"foo.fasta", "bar.fasta", "baz.zip"}
    for filename in file_list:
        (dts_dir / filename).touch()
        (dts_dir / filename).write_text(f"my name is {filename}")

    watcher = DTSFileWatcher(auth_client, config_tmp_path)
    # A little cheating here. Should probably scrape from logs. But it uses
    # the same code, at least.
    new_target_dir = watcher._make_unique_path(target_dir)
    assert not new_target_dir.exists()

    with patch(
        "staging_service.dts_file_watcher.awatch",
        new=make_mocked_awatch([(Change.added, str(manifest_path))]),
    ):
        with caplog.at_level("INFO", logger=LOGGER_NAME):
            await _run_watcher_once(watcher, wait_time=5)

    assert not any(target_dir.iterdir())

    assert new_target_dir.exists()
    assert new_target_dir.is_dir()
    file_list.add("manifest.json")
    for item in new_target_dir.iterdir():
        if item.is_file():
            assert item.name in file_list
            async with aiofiles.open(item) as infile:
                test_data = await infile.read()
                if item.name == "manifest.json":
                    assert test_data == manifest_text
                else:
                    assert test_data == f"my name is {item.name}"


def assert_watcher_health(
    health_status: DTSWatcherHealth,
    is_healthy: bool = True,
    is_watching: bool = True,
    config_dir: str = None,
):
    assert health_status.is_healthy == is_healthy
    assert health_status.is_watching == is_watching
    assert health_status.time_since_heartbeat >= 0
    assert health_status.watch_directory == config_dir
    assert health_status.health_check_timeout == HEALTH_CHECK_TIMEOUT_SEC


def test_initial_health(config_tmp_path, auth_client):
    """Test that watcher starts with proper initial heartbeat state."""
    # Before starting, should not be watching and not healthy
    watcher = DTSFileWatcher(auth_client, config_tmp_path)
    assert not watcher._is_watching
    assert not watcher.is_healthy()

    health_status = watcher.get_health_status()
    assert_watcher_health(
        health_status,
        is_healthy=False,
        is_watching=False,
        config_dir=str(config_tmp_path.dts_staging_dir),
    )


async def test_heartbeat_updates_during_watching(config_tmp_path, auth_client):
    """Test that heartbeat updates when watcher is active."""
    watcher = DTSFileWatcher(auth_client, config_tmp_path)
    initial_heartbeat = watcher._last_heartbeat

    await _run_watcher_once(watcher, wait_time=5)

    health = watcher.get_health_status()
    assert health.last_heartbeat > initial_heartbeat

    # Should be unhealthy once stopped
    assert not watcher.is_healthy()
    health = watcher.get_health_status()
    assert_watcher_health(
        health, is_healthy=False, is_watching=False, config_dir=str(config_tmp_path.dts_staging_dir)
    )


async def test_watching_state_changes(config_tmp_path, auth_client):
    watcher = DTSFileWatcher(auth_client, config_tmp_path)
    assert not watcher._is_watching

    with patch("staging_service.dts_file_watcher.awatch") as mock_awatch:

        async def mocked_events_generator():
            assert watcher._is_watching
            assert_watcher_health(
                watcher.get_health_status(), config_dir=str(config_tmp_path.dts_staging_dir)
            )
            watcher.stop_watching_for_files()
            yield []

        mock_awatch.return_value = mocked_events_generator()

        await watcher.start_watching_for_files()
        assert not watcher._is_watching


async def test_heartbeat_updates_on_timeout_iterations(auth_client, config_tmp_path):
    """Test that heartbeat updates even when awatch yields due to timeout."""
    heartbeats = []
    watcher = DTSFileWatcher(auth_client, config_tmp_path)

    with patch("staging_service.dts_file_watcher.awatch") as mock_awatch:

        async def mock_generator():
            # Record heartbeat before each yield
            heartbeats.append(watcher._last_heartbeat)
            yield []  # Empty changes (timeout case)

            # Small delay to ensure time difference
            await asyncio.sleep(0.01)
            heartbeats.append(watcher._last_heartbeat)
            yield []  # Another empty yield

            # Stop the watcher
            watcher._stop_event.set()

        mock_awatch.return_value = mock_generator()

        await watcher.start_watching_for_files()

        # Should have multiple heartbeat updates
        assert len(heartbeats) == 2
        assert heartbeats[1] > heartbeats[0]


async def test_health_check_during_file_processing(auth_client, config_tmp_path):
    """Test that heartbeat continues updating even during file processing."""
    watcher = DTSFileWatcher(auth_client, config_tmp_path)
    # Create a test manifest file
    test_dir = config_tmp_path.dts_staging_dir / "test_transfer"
    test_dir.mkdir()
    manifest_file = test_dir / "manifest.json"

    with patch("staging_service.dts_file_watcher.awatch") as mock_awatch:
        with patch.object(watcher, "_process_complete_manifest") as mock_process:
            # Make file processing take some time
            async def slow_process(path):
                await asyncio.sleep(0.1)
                # Verify heartbeat is still being updated during processing
                assert watcher.is_healthy()

            mock_process.side_effect = slow_process

            async def mock_generator():
                # Simulate file creation event
                yield [(Change.added, str(manifest_file))]
                watcher._stop_event.set()

            mock_awatch.return_value = mock_generator()

            await watcher.start_watching_for_files()

            # Process should have been called
            mock_process.assert_called_once_with(manifest_file)


def test_health_check_boundary_conditions(auth_client, config_tmp_path):
    """Test health check at exact timeout boundary."""
    watcher = DTSFileWatcher(auth_client, config_tmp_path)
    watcher._is_watching = True

    # Test exactly at timeout boundary
    watcher._last_heartbeat = time.time() - HEALTH_CHECK_TIMEOUT_SEC
    # Due to floating point precision, this might be healthy or not
    # Just verify it's consistent with the calculation
    assert watcher.is_healthy() == (
        watcher.get_health_status().time_since_heartbeat < HEALTH_CHECK_TIMEOUT_SEC
    )

    # Test just over timeout
    watcher._last_heartbeat = time.time() - (HEALTH_CHECK_TIMEOUT_SEC + 0.1)
    assert not watcher.is_healthy()

    # Test just under timeout
    watcher._last_heartbeat = time.time() - (HEALTH_CHECK_TIMEOUT_SEC - 0.1)
    assert watcher.is_healthy()


async def test_concurrent_health_checks(auth_client, config_tmp_path):
    """Test that concurrent health checks work correctly."""
    watcher = DTSFileWatcher(auth_client, config_tmp_path)
    watcher._is_watching = True
    watcher._last_heartbeat = time.time()

    # Run multiple health checks concurrently
    async def check_health():
        await asyncio.sleep(0.01)  # Small delay
        return watcher.is_healthy()

    tasks = [check_health() for _ in range(10)]
    results = await asyncio.gather(*tasks)

    # All should return True since watcher is healthy
    assert all(results)
