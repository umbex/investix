from datetime import timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.auth import require_session
from app.db import get_session
from app.models import Instrument, Observation, Operation

router = APIRouter(prefix="/api/quotes", tags=["quotes"], dependencies=[Depends(require_session)])


@router.get("")
def quotes(
    days: int = Query(default=90, ge=1, le=3650),
    session: Session = Depends(get_session),
) -> dict:
    instruments = list(
        session.scalars(
            select(Instrument)
            .where(
                or_(
                    Instrument.is_watch.is_(True),
                    Instrument.id.in_(select(Operation.instrument_id).where(Operation.cancelled.is_(False))),
                )
            )
            .order_by(Instrument.ticker)
        )
    )
    items: list[dict] = []
    for instrument in instruments:
        observations = list(
            session.scalars(
                select(Observation)
                .where(Observation.instrument_id == instrument.id)
                .order_by(Observation.observed_at.desc(), Observation.id.desc())
                .limit(2)
            )
        )
        latest = observations[0] if observations else None
        previous = observations[1] if len(observations) > 1 else None
        change_percent = None
        if latest is not None and previous is not None and previous.price:
            change_percent = ((latest.price - previous.price) / previous.price * Decimal("100")).quantize(Decimal("0.0000000001"))
        points = []
        if latest is not None:
            cutoff = latest.observed_at - timedelta(days=days)
            points = list(
                reversed(
                    list(
                        session.scalars(
                            select(Observation)
                            .where(Observation.instrument_id == instrument.id, Observation.observed_at >= cutoff)
                            .order_by(Observation.observed_at.desc(), Observation.id.desc())
                        )
                    )
                )
            )
        items.append({
            "ticker": instrument.ticker,
            "price_eur": latest.price if latest is not None else None,
            "change_percent": change_percent,
            "observed_at": latest.observed_at if latest is not None else None,
            "provider": latest.provider if latest is not None else None,
            "quote_symbol": instrument.quote_symbol or (latest.source_symbol if latest is not None else None) or instrument.ticker,
            "quote_venue": instrument.quote_venue or (latest.venue if latest is not None else None),
            "watch": instrument.is_watch,
            "has_position": session.scalar(select(Operation.id).where(Operation.instrument_id == instrument.id, Operation.cancelled.is_(False)).limit(1)) is not None,
            "points": [{"observed_at": point.observed_at, "price_eur": point.price} for point in points],
        })
    return {"days": days, "items": items}
