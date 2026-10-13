"""Entry point reserved for scheduled market-data work."""

import logging

logging.basicConfig(level=logging.INFO)
logging.getLogger(__name__).info("Investix worker started; no jobs are configured yet")
