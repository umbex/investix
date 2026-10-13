"""Long-running EOD worker; no public provider is enabled by default."""

import logging
import time
from collections.abc import Callable
from datetime import date
from decimal import Decimal

from app.providers.ecb import EcbUsdEurAdapter
from app.providers.twelve_data import TwelveDataAdapter
from app.services.market_data import refresh_instruments
from app.settings import Settings, get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def build_twelve_data_adapter(settings: Settings, *, fetch_fx: Callable[[date], Decimal] | None = None) -> TwelveDataAdapter | None:
    """Keep third-party market access opt-in even when the worker is running."""
    if not settings.twelve_data_api_key:
        return None
    resolver = fetch_fx or EcbUsdEurAdapter().fetch_rate
    return TwelveDataAdapter(
        api_key=settings.twelve_data_api_key,
        fx_to_eur=lambda observed_at: resolver(observed_at.date()),
    )


def refresh_once(settings: Settings, *, session_factory: Callable[[], object]) -> dict[str, list[str] | dict[str, str]]:
    provider = build_twelve_data_adapter(settings)
    if provider is None:
        return {"refreshed": [], "failed": {}}
    with session_factory() as session:  # type: ignore[union-attr]
        return refresh_instruments(session, lambda symbol, ticker: provider.fetch_latest(symbol, ticker=ticker))


def run() -> None:
    provider = build_twelve_data_adapter(get_settings())
    logger.info("Investix worker started; Twelve Data EOD provider %s", "configured" if provider else "disabled")
    while True:
        time.sleep(60)


if __name__ == "__main__":
    run()
