from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.portfolio_series import HistoricalOperation, HistoricalQuote, PortfolioSeries, build_portfolio_series
from app.models import Benchmark, Instrument, Observation, Operation


def benchmark_series(session: Session, portfolio: PortfolioSeries) -> list[dict]:
    active_benchmarks = list(session.scalars(select(Benchmark).where(Benchmark.active.is_(True)).order_by(Benchmark.name)))
    if not active_benchmarks or not portfolio.points:
        return []
    instruments = {instrument.ticker: instrument.id for instrument in session.scalars(select(Instrument).where(Instrument.ticker.in_([item.ticker for item in active_benchmarks]))) }
    observations_by_ticker: dict[str, list[tuple[date, Decimal]]] = {item.ticker: [] for item in active_benchmarks}
    for observation in session.scalars(select(Observation).where(Observation.instrument_id.in_(instruments.values())).order_by(Observation.observed_at, Observation.id)):
        ticker = next((name for name, instrument_id in instruments.items() if instrument_id == observation.instrument_id), None)
        if ticker is not None:
            observations_by_ticker[ticker].append((observation.observed_at.date(), Decimal(observation.price)))
    result: list[dict] = []
    for benchmark in active_benchmarks:
        latest: Decimal | None = None
        base: Decimal | None = None
        quote_index = 0
        quotes = observations_by_ticker[benchmark.ticker]
        points: list[dict] = []
        for portfolio_point in portfolio.points:
            while quote_index < len(quotes) and quotes[quote_index][0] <= portfolio_point.day:
                latest = quotes[quote_index][1]
                quote_index += 1
            if latest is None:
                continue
            if base is None:
                base = latest
            points.append({"date": portfolio_point.day.isoformat(), "return": latest / base - Decimal("1")})
        result.append({
            "name": benchmark.name,
            "ticker": benchmark.ticker,
            "quote_currency": benchmark.quote_currency,
            "methodology": benchmark.methodology,
            "points": points,
        })
    return result


def portfolio_series(session: Session, *, ticker: str | None = None) -> PortfolioSeries:
    instrument_query = select(Instrument)
    if ticker:
        instrument_query = instrument_query.where(Instrument.ticker == ticker.upper())
    instruments = {instrument.id: instrument.ticker for instrument in session.scalars(instrument_query)}
    operations = [
        HistoricalOperation(item.trade_date, item.kind, instruments[item.instrument_id], Decimal(item.quantity), Decimal(item.unit_price_eur))
        for item in session.scalars(select(Operation).where(Operation.cancelled.is_(False), Operation.instrument_id.in_(instruments)).order_by(Operation.trade_date, Operation.source_order, Operation.id))
    ]
    latest_by_day_and_instrument: dict[tuple[date, int], Observation] = {}
    for observation in session.scalars(select(Observation).where(Observation.instrument_id.in_(instruments)).order_by(Observation.observed_at, Observation.id)):
        # An EOD observation belongs to its provider-reported trading date.  Keep that
        # date stable even on database backends that return a timezone-naive timestamp.
        key = (observation.observed_at.date(), observation.instrument_id)
        latest_by_day_and_instrument[key] = observation
    quotes = [
        HistoricalQuote(day, instruments[observation.instrument_id], Decimal(observation.price))
        for (day, _), observation in latest_by_day_and_instrument.items()
    ]
    return build_portfolio_series(operations=operations, quotes=quotes)
