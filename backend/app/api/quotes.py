from datetime import timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
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
            .join(Operation, Operation.instrument_id == Instrument.id)
            .where(Operation.cancelled.is_(False))
            .distinct()
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
        if not observations:
            continue
        latest, previous = observations[0], observations[1] if len(observations) > 1 else None
        change_percent = None
        if previous is not None and previous.price:
            change_percent = ((latest.price - previous.price) / previous.price * Decimal("100")).quantize(Decimal("0.0000000001"))
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
            "price_eur": latest.price,
            "change_percent": change_percent,
            "observed_at": latest.observed_at,
            "provider": latest.provider,
            "points": [{"observed_at": point.observed_at, "price_eur": point.price} for point in points],
        })
    return {"days": days, "items": items}
