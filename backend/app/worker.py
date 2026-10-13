"""Entry point for explicit EOD/backfill jobs; no public provider is enabled by default."""

import logging

logging.basicConfig(level=logging.INFO)
logging.getLogger(__name__).info("Investix worker started; awaiting configured market-data job")
