from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Benchmark, Instrument
from app.schemas.benchmarks import BenchmarkConfig


def configure_benchmark(session: Session, payload: BenchmarkConfig) -> Benchmark:
    ticker = payload.ticker.upper()
    benchmark = session.scalar(select(Benchmark).where(Benchmark.ticker == ticker))
    values = payload.model_dump()
    values["ticker"] = ticker
    values["quote_currency"] = payload.quote_currency.upper()
    if benchmark is None:
        benchmark = Benchmark(**values)
        session.add(benchmark)
    else:
        for field, value in values.items():
            setattr(benchmark, field, value)
    instrument = session.scalar(select(Instrument).where(Instrument.ticker == ticker))
    if instrument is None:
        session.add(Instrument(ticker=ticker, quote_symbol=payload.quote_symbol, quote_venue=payload.quote_venue, quote_currency=payload.quote_currency.upper()))
    else:
        instrument.quote_symbol = payload.quote_symbol
        instrument.quote_venue = payload.quote_venue
        instrument.quote_currency = payload.quote_currency.upper()
    session.commit()
    session.refresh(benchmark)
    return benchmark


def serialize_benchmark(benchmark: Benchmark) -> dict:
    return {
        "name": benchmark.name,
        "ticker": benchmark.ticker,
        "quote_symbol": benchmark.quote_symbol,
        "quote_venue": benchmark.quote_venue,
        "quote_currency": benchmark.quote_currency,
        "methodology": benchmark.methodology,
        "active": benchmark.active,
        "note": benchmark.note,
    }
