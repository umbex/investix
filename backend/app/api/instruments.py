from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import require_session
from app.db import get_session
from app.models import Instrument, Operation
from app.schemas.instruments import WatchInstrumentConfig

router = APIRouter(prefix="/api/instruments", tags=["instruments"], dependencies=[Depends(require_session)])
MAX_WATCH_INSTRUMENTS = 5


def _serialize(instrument: Instrument, *, has_position: bool) -> dict:
    return {
        "ticker": instrument.ticker,
        "quote_symbol": instrument.quote_symbol,
        "quote_venue": instrument.quote_venue,
        "quote_currency": instrument.quote_currency,
        "watch": instrument.is_watch,
        "has_position": has_position,
    }


@router.get("/catalog")
def catalog(session: Session = Depends(get_session)) -> list[dict]:
    instruments = list(session.scalars(select(Instrument).order_by(Instrument.ticker)))
    return [
        _serialize(
            instrument,
            has_position=session.scalar(select(Operation.id).where(Operation.instrument_id == instrument.id, Operation.cancelled.is_(False)).limit(1)) is not None,
        )
        for instrument in instruments
    ]


@router.put("/watch/{ticker}")
def configure_watch(ticker: str, payload: WatchInstrumentConfig, session: Session = Depends(get_session)) -> dict:
    normalized_ticker = ticker.strip().upper()
    if not normalized_ticker:
        raise HTTPException(status_code=422, detail="Ticker is required")
    instrument = session.scalar(select(Instrument).where(Instrument.ticker == normalized_ticker))
    if instrument is None:
        if payload.watch and session.scalar(select(func.count(Instrument.id)).where(Instrument.is_watch.is_(True))) >= MAX_WATCH_INSTRUMENTS:
            raise HTTPException(status_code=422, detail=f"At most {MAX_WATCH_INSTRUMENTS} watch instruments are allowed")
        instrument = Instrument(ticker=normalized_ticker)
        session.add(instrument)
    elif payload.watch and not instrument.is_watch and session.scalar(select(func.count(Instrument.id)).where(Instrument.is_watch.is_(True))) >= MAX_WATCH_INSTRUMENTS:
        raise HTTPException(status_code=422, detail=f"At most {MAX_WATCH_INSTRUMENTS} watch instruments are allowed")
    instrument.quote_symbol = payload.quote_symbol.strip().upper()
    instrument.quote_venue = payload.quote_venue.strip()
    instrument.quote_currency = payload.quote_currency.strip().upper()
    instrument.is_watch = payload.watch
    session.commit()
    session.refresh(instrument)
    has_position = session.scalar(select(Operation.id).where(Operation.instrument_id == instrument.id, Operation.cancelled.is_(False)).limit(1)) is not None
    return _serialize(instrument, has_position=has_position)
