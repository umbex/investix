from collections import defaultdict
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import require_session
from app.db import get_session
from app.domain.ledger import LedgerOperation, rebuild_position
from app.models import Instrument, Operation

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"], dependencies=[Depends(require_session)])


@router.get("")
def summary(session: Session = Depends(get_session)) -> dict:
    operations = list(session.scalars(select(Operation).where(Operation.cancelled.is_(False)).order_by(Operation.trade_date, Operation.source_order, Operation.id)))
    by_instrument: dict[int, list[Operation]] = defaultdict(list)
    for operation in operations:
        by_instrument[operation.instrument_id].append(operation)
    positions = []
    for instrument_id, items in by_instrument.items():
        snapshot = rebuild_position([
            LedgerOperation(id=item.id, trade_date=item.trade_date, source_order=item.source_order, kind=item.kind, quantity=Decimal(item.quantity), unit_price_eur=Decimal(item.unit_price_eur), fee_eur=Decimal(item.fee_eur) if item.fee_eur is not None else None, dividend_eur=Decimal(item.dividend_eur) if item.dividend_eur is not None else None)
            for item in items
            if item.kind in {"BUY", "SELL", "DIVIDEND", "FEE"}
        ])
        instrument = session.get(Instrument, instrument_id)
        positions.append({"ticker": instrument.ticker, "quantity": snapshot.quantity, "open_cost_eur": snapshot.open_cost_eur, "realized_pnl_eur": snapshot.realized.pnl_eur})
    return {"positions": positions, "valuation_status": "unavailable_without_observation"}
