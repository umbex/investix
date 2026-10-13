"""Long-running EOD worker; no public provider is enabled by default."""

import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run() -> None:
    logger.info("Investix worker started; awaiting configured market-data job")
    while True:
        time.sleep(60)


if __name__ == "__main__":
    run()
