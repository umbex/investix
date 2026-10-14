"""Long-running EOD worker; no public provider is enabled by default."""

import logging
import json
import os
import time
from collections.abc import Callable
from datetime import date, datetime, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from app.providers.ecb import EcbUsdEurAdapter
from app.providers.twelve_data import TwelveDataAdapter
from app.services.market_data import refresh_instruments
from app.settings import Settings, get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
MARKET_SCHEDULES = {"EU": (18, 0), "US": (16, 30)}
MARKET_TIMEZONES = {"EU": ZoneInfo("Europe/Rome"), "US": ZoneInfo("America/New_York")}


def due_market_jobs(now, *, last_runs: dict[str, date], market: str | None = None) -> list[str]:
    """Return one daily job per market once its scheduled time has passed.

    Using ``>=`` instead of exact minute matching allows the worker to recover
    after a restart, a delayed loop iteration, or a short container outage.
    """
    current = (now.hour, now.minute)
    candidates = [(name, scheduled) for name, scheduled in MARKET_SCHEDULES.items() if (market is None or name == market) and current >= scheduled and last_runs.get(name) != now.date()]
    if market is None:
        # The helper historically received one market's local clock. When
        # called without an explicit market, only recover a schedule crossed
        # within the last hour; the timezone-aware caller below handles full
        # downtime recovery for every market explicitly.
        elapsed = [(name, scheduled, current[0] * 60 + current[1] - (scheduled[0] * 60 + scheduled[1])) for name, scheduled in candidates]
        candidates = [(name, scheduled) for name, scheduled, minutes in elapsed if minutes <= 60]
    return [name for name, _ in candidates]


def due_jobs_at(now_utc, *, last_runs: dict[str, date]) -> list[str]:
    """Evaluate each scheduled job in the timezone of its own market."""
    due: list[str] = []
    for market, timezone in MARKET_TIMEZONES.items():
        local = now_utc.astimezone(timezone)
        if market in due_market_jobs(local, last_runs=last_runs, market=market):
            due.append(market)
    return due


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
        return refresh_instruments(session, lambda symbol, ticker, venue: provider.fetch_latest(symbol, ticker=ticker, exchange=venue))


def run_scheduled_once(
    settings: Settings,
    *,
    now_utc: datetime,
    last_runs: dict[str, date],
    session_factory: Callable[[], object],
) -> dict[str, dict[str, list[str] | dict[str, str]]]:
    """Run each due market once and record the local calendar date on success."""
    results: dict[str, dict[str, list[str] | dict[str, str]]] = {}
    for market in due_jobs_at(now_utc, last_runs=last_runs):
        try:
            results[market] = refresh_once(settings, session_factory=session_factory)
        except Exception:
            logger.exception("Scheduled %s market refresh failed", market)
            continue
        local_date = now_utc.astimezone(MARKET_TIMEZONES[market]).date()
        last_runs[market] = local_date
    return results


def write_worker_status(
    settings: Settings,
    *,
    now_utc: datetime,
    last_runs: dict[str, date],
    results: dict[str, dict[str, list[str] | dict[str, str]]],
) -> None:
    """Publish a non-secret heartbeat when an explicit status path is configured."""
    if not settings.worker_status_file:
        return
    destination = settings.worker_status_file
    payload = {
        "status": "ok",
        "updated_at": now_utc.isoformat(),
        "provider": "twelve_data" if settings.twelve_data_api_key else "disabled",
        "last_runs": {market: day.isoformat() for market, day in last_runs.items()},
        "last_results": results,
    }
    temporary = f"{destination}.partial"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
    os.replace(temporary, destination)


def run() -> None:
    from app.db import create_session_factory

    settings = get_settings()
    provider = build_twelve_data_adapter(settings)
    logger.info("Investix worker started; Twelve Data EOD provider %s", "configured" if provider else "disabled")
    last_runs: dict[str, date] = {}
    session_factory = create_session_factory()
    while True:
        now_utc = datetime.now(timezone.utc)
        results = run_scheduled_once(settings, now_utc=now_utc, last_runs=last_runs, session_factory=session_factory)
        write_worker_status(settings, now_utc=now_utc, last_runs=last_runs, results=results)
        time.sleep(60)


if __name__ == "__main__":
    run()
