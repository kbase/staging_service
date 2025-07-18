from typing import Callable, Tuple
import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from staging_service.dts_file_watcher import DTSFileWatcher
from pathlib import Path
from watchfiles import Change


async def _run_watcher_once(watcher: DTSFileWatcher):
    """
    A convenience method that starts and stops the watcher at its first cycle.
    """
    task = asyncio.create_task(watcher.start_watching_for_files())
    watcher.stop_watching_for_files()
    await task


def make_mocked_awatch(returned_events: list[Tuple[Change, str]]) -> Callable:
    async def fake_awatch(*args, **kwargs):
        yield returned_events

    return fake_awatch


async def test_dts_file_watcher_loop_runs_and_stops(tmp_path):
    watcher = DTSFileWatcher(None, None, tmp_path)

    task = asyncio.create_task(watcher.start_watching_for_files())
    await asyncio.sleep(1)  # give it time to enter the loop
    watcher.stop_watching_for_files()
    await asyncio.wait_for(task, timeout=2)
    assert task.done()


async def test_top_level_manifest_ignored(tmp_path):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.touch()

    watcher = DTSFileWatcher(None, None, tmp_path)
    watcher._process_complete_manifest = AsyncMock()

    with patch(
        "staging_service.dts_file_watcher.awatch",
        new=make_mocked_awatch([(Change.added, str(manifest_path))]),
    ):
        await _run_watcher_once(watcher)

    watcher._process_complete_manifest.assert_not_awaited()


async def test_manifest_found(tmp_path):
    manifest_dir = tmp_path / "subdir"
    manifest_dir.mkdir()
    manifest_path = manifest_dir / "manifest.json"
    manifest_path.touch()

    watcher = DTSFileWatcher(None, None, tmp_path)
    watcher._process_complete_manifest = AsyncMock()

    with patch(
        "staging_service.dts_file_watcher.awatch",
        new=make_mocked_awatch([(Change.added, str(manifest_path))]),
    ):
        await _run_watcher_once(watcher)

    watcher._process_complete_manifest.assert_awaited()


async def test_dts_file_watcher_fail_no_dir():
    fake_dir = Path("/not/a/real/directory")
    watcher = DTSFileWatcher(None, None, fake_dir)
    with pytest.raises(FileNotFoundError, match="Not watching for DTS files"):
        await watcher.start_watching_for_files()
