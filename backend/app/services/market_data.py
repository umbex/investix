from collections.abc import Callable
from datetime import datetime, timedelta
from time import sleep as default_sleep
from typing import TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Instrument, Observation
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
    )
    session.add(stored)
    session.commit()
    session.refresh(stored)
    return stored
