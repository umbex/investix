from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.domain.money import normalize_price_to_eur


class ProviderError(Exception):
    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


@dataclass(frozen=True)
class MarketObservation:
    provider: str
    ticker: str
    observed_at: datetime
    raw_price: Decimal
    currency: str
    fx_to_eur: Decimal
    normalized_price_eur: Decimal
    source_symbol: str | None = None
    venue: str | None = None
    quote_unit: str | None = None
    price_field: str | None = "close"
    status: str = "valid"
    fx_provider: str | None = None


@dataclass(frozen=True)
class LiveQuote:
    ticker: str
    price: Decimal
    change_percent: Decimal | None
    observed_at: datetime
    currency: str
    price_eur: Decimal | None
    provider: str
    source_symbol: str | None = None
    status: str = "fresh"
    raw: dict | None = None


def normalize_observation(
    *, provider: str,
    ticker: str,
    observed_at: datetime,
    raw_price: Decimal,
    currency: str,
    fx_to_eur: Decimal,
) -> MarketObservation:
    if raw_price <= 0:
        raise ProviderError("Il prezzo deve essere positivo")
    if fx_to_eur <= 0:
        raise ProviderError("Il cambio deve essere positivo")
    return MarketObservation(
        provider=provider,
        ticker=ticker.upper(),
        observed_at=observed_at,
        raw_price=raw_price,
        currency=currency.upper(),
        fx_to_eur=fx_to_eur,
        normalized_price_eur=normalize_price_to_eur(raw_price, currency, fx_to_eur),
    )
