from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.portfolio_series import HistoricalOperation, HistoricalQuote, PortfolioSeries, build_portfolio_series
from app.models import Instrument, Observation, Operation


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
