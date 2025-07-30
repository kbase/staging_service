import argparse
from dataclasses import asdict
import logging
from pathlib import Path
import sys
from staging_service.config import StagingServiceConfig
from staging_service.dts_file_watcher import DTSFileWatcher
from staging_service.kb_auth_client import InvalidTokenError, KBaseAuth
from staging_service.utils import Path as StagingPath
import asyncio
import os
import uvloop
import signal

CONFIG_ENV = "KB_DEPLOYMENT_CONFIG"
HEALTH_CHECK_INTERVAL = 10

EXIT_NORMAL = 0
EXIT_WATCHER_FAIL = 1
EXIT_MISSING_CONFIG = 2
EXIT_BAD_CONFIG = 3
EXIT_UNKNOWN = 10

logger = logging.getLogger("run_dts_watcher")


def get_config() -> StagingServiceConfig:
    if not os.environ.get(CONFIG_ENV):
        raise FileNotFoundError(f"Missing required config environment variable: {CONFIG_ENV}")
    return StagingServiceConfig(os.environ[CONFIG_ENV])


class DTSWatcherService:
    """
    A class for handling running the DTS File Watcher. This wraps the main
    class in some signal and health tracking, and shuts it down gracefully
    either when requested, or when a failure occurs.
    """

    @classmethod
    async def create(cls, config: StagingServiceConfig):
        """
        Make this class. Needs to be async so it can asyncronously make an auth client.
        """
        auth_client = await KBaseAuth.create(config.auth_url)
        # This is really just to test the auth token. The answer doesn't matter, as long as it
        # doesn't raise an exception. Raised exceptions are allowed out.
        await auth_client.is_valid_user("should_never_be_a_valid_user_probably", config.auth_token)
        return DTSWatcherService(config, auth_client)

    def __init__(self, config: StagingServiceConfig, auth_client: KBaseAuth):
        """
        This init class is not expected to be called directly, use `create` instead.
        """
        self.config = config
        self.shutdown_event = asyncio.Event()
        self.watcher = DTSFileWatcher(auth_client, config)

    async def _health_monitor(self) -> int:
        """
        Monitor the health of the watcher. This expects the watcher to be running.
        This makes a looping task that will check the service's DTS watcher every
        HEALTH_CHECK_INTERVAL seconds.
        If it is not healthy (is_healthy returns False), it triggers the shutdown
        event and logs the last health result.
        """
        while not self.shutdown_event.is_set():
            await asyncio.sleep(HEALTH_CHECK_INTERVAL)

            if not self.shutdown_event.is_set():
                logger.debug("Checking watcher health")
                if not self.watcher.is_healthy():
                    logger.error(
                        f"Watcher is no longer healthy: {asdict(self.watcher.get_health_status())}"
                    )
                    return EXIT_WATCHER_FAIL
                logger.debug(f"Watcher health ok, waiting {HEALTH_CHECK_INTERVAL} sec")

    async def run(self) -> int:
        """
        The main watcher startup function.
        This runs the following ways:
        1. Sets up tasks for the DTS file watcher and its health monitor.
        2. Makes an additional task for the shutdown event to wait on.
        3. If any of those tasks complete, shut down the rest of them and return.
        4. Log and return any errors from the watcher if they arise.
        """
        watcher_task = asyncio.create_task(self.watcher.start_watching_for_files())

        done, pending = await asyncio.wait(
            [
                watcher_task,
                asyncio.create_task(self._health_monitor()),
                asyncio.create_task(self.shutdown_event.wait()),
            ],
            return_when=asyncio.FIRST_COMPLETED,
        )

        # Check if the watcher task completed with an exception
        if watcher_task in done:
            try:
                await watcher_task  # This will raise the exception if there was one
            except Exception as e:
                logger.error(f"DTS File Watcher failed: {e}")
                return EXIT_WATCHER_FAIL

        if self.shutdown_event.is_set():
            logger.info("Shutdown requested, stopping watcher.")
            self.watcher.stop_watching_for_files()

            try:
                await asyncio.wait_for(watcher_task, timeout=30)
            except asyncio.TimeoutError:
                logger.warning("Watcher didn't stop gracefully, forcing it to stop")
                await self.graceful_cancel(watcher_task)

        for task in pending:
            await self.graceful_cancel(task)

        await asyncio.gather(*pending, return_exceptions=True)
        return EXIT_NORMAL

    async def graceful_cancel(self, task: asyncio.Task):
        """
        Gracefully-ish forces a task to cancel. This captures (and ignores)
        any CancelledErrors that occur during cancellation.
        """
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    def stop(self):
        """
        Stops the running from running.
        """
        self.shutdown_event.set()


async def main(config: StagingServiceConfig) -> int:
    """
    The main function here. This does the following:
    1. Sets up the DTS file watcher service.
    2. Gets it ready to run in an asyncio loop.
    3. Attaches SIGTERM and SIGINT to cancel handlers.
    4. Runs it and just hangs out until it either cancels or dies.
    """
    try:
        service = await DTSWatcherService.create(config)
    except InvalidTokenError as err:
        logger.error(f"Invalid auth token in config, unable to start watcher: {err}")
        return EXIT_BAD_CONFIG
    except Exception as err:
        logger.error(f"Unexpected error while initializing DTSWatcherService: {err}")
        return EXIT_UNKNOWN

    def signal_handler(signum):
        logger.info(f"Signal {signum} received, stopping watcher.")
        service.stop()

    loop = asyncio.get_running_loop()
    for sig in [signal.SIGTERM, signal.SIGINT]:
        loop.add_signal_handler(sig, signal_handler, sig)

    return await service.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Runs the Data Transfer Service file watcher")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    log_level = logging.INFO
    if args.debug:
        log_level = logging.DEBUG

    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    # get the config loaded, or fail early
    try:
        config = get_config()
        # make sure the dts dir and data dir exist
        if not Path(config.data_dir).exists():
            raise ValueError(f"User staging data directory {config.data_dir} not found. Stopping.")
        if not Path(config.dts_staging_dir).exists():
            raise ValueError(f"DTS staging directory {config.dts_staging_dir} not found. Stopping.")
        # I don't like that I have to do this, see issue #225
        StagingPath._DATA_DIR = config.data_dir
        StagingPath._META_DIR = config.meta_dir
    except ValueError as e:
        logger.error(f"Config error: {e}")
        sys.exit(EXIT_BAD_CONFIG)
    except FileNotFoundError as e:
        logger.error(e)
        sys.exit(EXIT_MISSING_CONFIG)

    try:
        sys.exit(asyncio.run(main(config)))
    except KeyboardInterrupt:
        logger.info("Canceled by user")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        sys.exit(EXIT_UNKNOWN)
