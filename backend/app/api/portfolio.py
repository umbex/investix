from collections import defaultdict
from datetime import date
from decimal import Decimal

import csv
from io import StringIO

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import require_session
from app.db import get_session
from app.domain.ledger import LedgerOperation, rebuild_position
from app.models import Account, Instrument, Observation, Operation

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"], dependencies=[Depends(require_session)])


def _as_ledger_operation(item: Operation) -> LedgerOperation:
    return LedgerOperation(
        id=item.id,
        trade_date=item.trade_date,
        source_order=item.source_order,
        kind=item.kind,
        quantity=Decimal(item.quantity),
        unit_price_eur=Decimal(item.unit_price_eur),
        fee_eur=Decimal(item.fee_eur) if item.fee_eur is not None else None,
        dividend_eur=Decimal(item.dividend_eur) if item.dividend_eur is not None else None,
    )


def _positions(session: Session, *, ticker: str | None = None, account: str | None = None) -> list[dict]:
    statement = select(Operation).where(Operation.cancelled.is_(False)).order_by(Operation.trade_date, Operation.source_order, Operation.id)
    if ticker:
        instrument_ids = select(Instrument.id).where(Instrument.ticker == ticker.upper())
        statement = statement.where(Operation.instrument_id.in_(instrument_ids))
    if account:
        account_ids = select(Account.id).where(Account.name == account)
        statement = statement.where(Operation.account_id.in_(account_ids))
    operations = list(session.scalars(statement))
    by_account_instrument: dict[tuple[int, int], list[Operation]] = defaultdict(list)
    for operation in operations:
        by_account_instrument[(operation.account_id, operation.instrument_id)].append(operation)
    by_instrument: dict[int, list[dict]] = defaultdict(list)
    for (account_id, instrument_id), items in by_account_instrument.items():
        snapshot = rebuild_position([_as_ledger_operation(item) for item in items])
        by_instrument[instrument_id].append({"name": session.get(Account, account_id).name, "snapshot": snapshot})

    positions: list[dict] = []
    for instrument_id, account_snapshots in by_instrument.items():
        instrument = session.get(Instrument, instrument_id)
        latest = session.scalar(
            select(Observation)
            .where(Observation.instrument_id == instrument_id)
            .order_by(Observation.observed_at.desc(), Observation.id.desc())
            .limit(1)
        )
        quantity = sum((item["snapshot"].quantity for item in account_snapshots), Decimal("0"))
        open_cost = sum((item["snapshot"].open_cost_eur for item in account_snapshots), Decimal("0"))
        realized = sum((item["snapshot"].realized.pnl_eur for item in account_snapshots), Decimal("0"))
        market_value = quantity * Decimal(latest.price) if latest is not None else None
        fees = [item["snapshot"].fees for item in account_snapshots]
        dividends = [item["snapshot"].dividends for item in account_snapshots]
        positions.append({
            "ticker": instrument.ticker,
            "quantity": quantity,
            "open_cost_eur": open_cost,
            "average_cost_eur": open_cost / quantity if quantity else Decimal("0"),
            "realized_pnl_eur": realized,
            "market_value_eur": market_value,
            "unrealized_pnl_eur": market_value - open_cost if market_value is not None else None,
            "fees_eur": sum((item.recorded_eur or Decimal("0") for item in fees), Decimal("0")) if fees and all(item.recorded_eur is not None for item in fees) else None,
            "dividends_eur": sum((item.recorded_eur or Decimal("0") for item in dividends), Decimal("0")) if dividends and all(item.recorded_eur is not None for item in dividends) else None,
            "market_data_status": "available" if latest is not None else "missing",
            "last_observed_at": latest.observed_at if latest is not None else None,
            "market_data_provider": latest.provider if latest is not None else None,
            "market_data_source_symbol": latest.source_symbol if latest is not None else None,
            "market_data_venue": latest.venue if latest is not None else None,
            "market_data_fx_provider": latest.fx_provider if latest is not None else None,
            "accounts": [
                {
                    "name": item["name"],
                    "quantity": item["snapshot"].quantity,
                    "open_cost_eur": item["snapshot"].open_cost_eur,
                    "realized_pnl_eur": item["snapshot"].realized.pnl_eur,
                }
                for item in account_snapshots
            ],
        })
    return sorted(positions, key=lambda item: item["ticker"])


def _summary(positions: list[dict]) -> dict:
    values = [item["market_value_eur"] for item in positions]
    has_all_values = bool(positions) and all(value is not None for value in values)
    market_value = sum(values, Decimal("0")) if has_all_values else None
    open_cost = sum((item["open_cost_eur"] for item in positions), Decimal("0"))
    realized = sum((item["realized_pnl_eur"] for item in positions), Decimal("0"))
    allocations = [
        {
            "ticker": item["ticker"],
            "market_value_eur": item["market_value_eur"],
            "weight": item["market_value_eur"] / market_value if has_all_values and market_value else None,
            "open_cost_eur": item["open_cost_eur"],
            "cost_weight": item["open_cost_eur"] / open_cost if open_cost else None,
            "accounts": [
                {
                    "account": account["name"],
                    "open_cost_eur": account["open_cost_eur"],
                    "weight": account["open_cost_eur"] / item["open_cost_eur"] if item["open_cost_eur"] else None,
                }
                for account in item["accounts"]
            ],
        }
        for item in positions
    ]
    account_costs: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for position in positions:
        for account in position["accounts"]:
            account_costs[account["name"]] += account["open_cost_eur"]
    account_allocations = [
        {"account": name, "open_cost_eur": cost, "weight": cost / open_cost if open_cost else None}
        for name, cost in sorted(account_costs.items())
    ]
    return {
        "positions": positions,
        "allocations": allocations,
        "account_allocations": account_allocations,
        "kpis": {
            "open_cost_eur": open_cost,
            "market_value_eur": market_value,
            "realized_pnl_eur": realized,
            "unrealized_pnl_eur": market_value - open_cost if market_value is not None else None,
        },
        "valuation_status": "available" if has_all_values else "unavailable_without_observation",
    }


@router.get("")
def summary(
    ticker: str | None = Query(default=None),
    account: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> dict:
    return _summary(_positions(session, ticker=ticker, account=account))


@router.get("/export.csv")
def export_csv(
    ticker: str | None = Query(default=None),
    account: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> Response:
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=["ticker", "quantity", "open_cost_eur", "market_value_eur", "realized_pnl_eur", "unrealized_pnl_eur", "market_data_status"])
    writer.writeheader()
    for item in _positions(session, ticker=ticker, account=account):
        writer.writerow({field: item[field] for field in writer.fieldnames})
    return Response(output.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=investix-posizioni.csv"})
