"""Reconcile a staged STOCKS-26 import against the authoritative ledger."""

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.importing.reconcile import reconcile_quantities
from app.importing.stocks26 import ImportPreview
from app.models import Account, Instrument, Operation


@dataclass(frozen=True)
class LedgerReconciliation:
    reference_quantities: dict[str, Decimal]
    ledger_quantities: dict[str, Decimal]
    quantity_status: str


def reconcile_preview_with_ledger(session: Session, preview: ImportPreview) -> LedgerReconciliation:
    if preview.errors:
        raise ValueError("La preview contiene righe non valide")
    reference_quantities: dict[str, Decimal] = {}
    for row in preview.rows:
        key = f"{row.ticker}|{row.account_name}"
        reference_quantities[key] = reference_quantities.get(key, Decimal("0")) + _quantity_delta(row.kind, row.quantity)

    ledger_quantities: dict[str, Decimal] = {}
    statement = (
        select(Operation, Account.name, Instrument.ticker)
        .join(Account, Account.id == Operation.account_id)
        .join(Instrument, Instrument.id == Operation.instrument_id)
        .where(Operation.cancelled.is_(False))
    )
    for operation, account_name, ticker in session.execute(statement):
        key = f"{ticker}|{account_name}"
        ledger_quantities[key] = ledger_quantities.get(key, Decimal("0")) + _quantity_delta(operation.kind, Decimal(operation.quantity))

    reconcile_quantities(ledger_quantities, reference_quantities)
    return LedgerReconciliation(reference_quantities, ledger_quantities, "matched")


def _quantity_delta(kind: str, quantity: Decimal) -> Decimal:
    if kind in {"BUY", "SPLIT"}:
        return quantity
    if kind == "SELL":
        return -quantity
    return Decimal("0")
