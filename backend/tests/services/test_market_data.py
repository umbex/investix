from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.providers.base import MarketObservation, ProviderError
from app.services.market_data import fetch_with_retry, is_stale, persist_observation


def observation() -> MarketObservation:
    return MarketObservation(
        provider="manual-csv",
        ticker="VWCE",
        observed_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        raw_price=Decimal("100"),
        currency="EUR",
        fx_to_eur=Decimal("1"),
        normalized_price_eur=Decimal("100"),
    )


def test_retries_rate_limited_provider_once_then_returns_value() -> None:
    calls = 0

    def fetch():
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ProviderError("rate limit", retryable=True)
        return observation()

    assert fetch_with_retry(fetch, retries=1, sleep=lambda _: None) == observation()
    assert calls == 2


def test_non_retryable_provider_error_is_not_hidden() -> None:
    with pytest.raises(ProviderError, match="simbolo"):
        fetch_with_retry(lambda: (_ for _ in ()).throw(ProviderError("simbolo", retryable=False)), retries=2, sleep=lambda _: None)


def test_staleness_remains_visible() -> None:
    now = datetime(2026, 1, 10, tzinfo=timezone.utc)
    assert is_stale(observation(), now=now, max_age=timedelta(days=2)) is True


def test_persistence_is_idempotent_for_the_same_provider_timestamp() -> None:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from app.models import Base

    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        first = persist_observation(session, observation())
        second = persist_observation(session, observation())

    assert first.id == second.id
