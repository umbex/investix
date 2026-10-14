"""Explicit instrument identity and preferred quote configuration."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Instrument


def configure_instrument(
    session: Session,
    *,
    ticker: str,
    isin: str | None,
    quote_symbol: str,
    quote_venue: str,
    quote_currency: str,
) -> Instrument:
    normalized_ticker = ticker.upper()
    instrument = session.scalar(select(Instrument).where(Instrument.ticker == normalized_ticker))
    if instrument is None:
        instrument = Instrument(ticker=normalized_ticker)
        session.add(instrument)
    instrument.isin = isin.upper() if isin else None
    instrument.quote_symbol = quote_symbol.upper()
    instrument.quote_venue = quote_venue
    instrument.quote_currency = quote_currency.upper()
    session.flush()
    return instrument
