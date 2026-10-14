from collections.abc import Callable
from collections.abc import Callable, Iterable
from datetime import date, datetime, timedelta
from time import sleep as default_sleep
from typing import TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Instrument, Observation, Operation
from app.providers.base import MarketObservation, ProviderError

T = TypeVar("T")


def fetch_with_retry(fetch: Callable[[], T], *, retries: int, sleep: Callable[[float], None] = default_sleep) -> T:
    for attempt in range(retries + 1):
        try:
            return fetch()
        except ProviderError as error:
            if not error.retryable or attempt == retries:
                raise
            sleep(2**attempt)
    raise RuntimeError("unreachable")


def is_stale(observation: MarketObservation, *, now: datetime, max_age: timedelta) -> bool:
    return now - observation.observed_at > max_age


def persist_observation(session: Session, market_observation: MarketObservation) -> Observation:
    instrument = session.scalar(select(Instrument).where(Instrument.ticker == market_observation.ticker))
    if instrument is None:
        instrument = Instrument(ticker=market_observation.ticker)
        session.add(instrument)
        session.flush()
    existing = session.scalar(
        select(Observation).where(
            Observation.instrument_id == instrument.id,
            Observation.provider == market_observation.provider,
            Observation.observed_at == market_observation.observed_at,
        )
    )
    if existing is not None:
        return existing
    stored = Observation(
        instrument_id=instrument.id,
        provider=market_observation.provider,
        price=market_observation.normalized_price_eur,
        raw_price=market_observation.raw_price,
        currency=market_observation.currency,
        fx_to_eur=market_observation.fx_to_eur,
        observed_at=market_observation.observed_at,
        source_symbol=market_observation.source_symbol or market_observation.ticker,
        venue=market_observation.venue,
        quote_unit=market_observation.quote_unit,
        price_field=market_observation.price_field,
        status=market_observation.status,
        fx_provider=market_observation.fx_provider,
    )
    session.add(stored)
    session.commit()
    session.refresh(stored)
    return stored


def refresh_instruments(
    session: Session,
    fetch: Callable[[str, str, str | None], MarketObservation],
) -> dict[str, list[str] | dict[str, str]]:
    """Refresh every configured quote symbol without turning one provider error into data loss."""
    refreshed: list[str] = []
    failed: dict[str, str] = {}
    instruments = list(session.scalars(select(Instrument).where(Instrument.quote_symbol.is_not(None)).order_by(Instrument.ticker)))
    for instrument in instruments:
        try:
            persist_observation(session, fetch(instrument.quote_symbol, instrument.ticker, instrument.quote_venue))
            refreshed.append(instrument.ticker)
        except ProviderError as error:
            session.rollback()
            failed[instrument.ticker] = str(error)
    return {"refreshed": refreshed, "failed": failed}


def backfill_instrument(
    session: Session,
    instrument: Instrument,
    fetch_history: Callable[[str, str, date, date, str | None], Iterable[MarketObservation]],
    *,
    end_date: date | None = None,
) -> dict[str, str | int]:
    """Backfill provider-supplied points from the first ledger operation onward."""
    if not instrument.quote_symbol:
        return {"ticker": instrument.ticker, "status": "missing_quote_symbol", "observations": 0}
    start_date = session.scalar(select(func.min(Operation.trade_date)).where(Operation.instrument_id == instrument.id, Operation.cancelled.is_(False)))
    if start_date is None:
        return {"ticker": instrument.ticker, "status": "no_operations", "observations": 0}
    end = end_date or date.today()
    if end < start_date:
        return {"ticker": instrument.ticker, "status": "empty_range", "observations": 0}
    observations = 0
    for market_observation in fetch_history(instrument.quote_symbol, instrument.ticker, start_date, end, instrument.quote_venue):
        persist_observation(session, market_observation)
        observations += 1
    return {"ticker": instrument.ticker, "status": "backfilled", "observations": observations}
