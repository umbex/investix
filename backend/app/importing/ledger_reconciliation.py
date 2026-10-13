"""Reconcile a staged STOCKS-26 import against the authoritative ledger."""

from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.ledger import LedgerOperation, rebuild_position
from app.importing.reconcile import ReconciliationTolerance
from app.importing.stocks26 import ImportPreview
from app.models import Account, Instrument, Operation


@dataclass(frozen=True)
class LedgerReconciliation:
    reference_quantities: dict[str, Decimal]
    ledger_quantities: dict[str, Decimal]
    quantity_status: str
    reference_cost_eur: dict[str, Decimal] = field(default_factory=dict)
    ledger_cost_eur: dict[str, Decimal] = field(default_factory=dict)
    reference_realized_pnl_eur: dict[str, Decimal] = field(default_factory=dict)
    ledger_realized_pnl_eur: dict[str, Decimal] = field(default_factory=dict)
    cost_status: str = "matched"
    realized_pnl_status: str = "matched"
    differences: dict[str, tuple[Decimal, Decimal]] = field(default_factory=dict)
    tolerance: ReconciliationTolerance = ReconciliationTolerance()
    reference_average_cost_eur: dict[str, Decimal] = field(default_factory=dict)
    ledger_average_cost_eur: dict[str, Decimal] = field(default_factory=dict)
    average_cost_status: str = "matched"
    coverage: dict[str, str] = field(default_factory=lambda: {"dividends": "not_comparable", "benchmarks": "not_comparable"})

    @property
    def passed(self) -> bool:
        return self.quantity_status == "matched" and self.cost_status == "matched" and self.realized_pnl_status == "matched" and self.average_cost_status == "matched"

    def as_dict(self) -> dict:
        return {
            "passed": self.passed,
            "quantity_tolerance": str(self.tolerance.quantity),
            "cost_tolerance_eur": str(self.tolerance.cost_eur),
            "realized_pnl_tolerance_eur": str(self.tolerance.realized_pnl_eur),
            "reference_quantities": _serialize(self.reference_quantities),
            "ledger_quantities": _serialize(self.ledger_quantities),
            "reference_cost_eur": _serialize(self.reference_cost_eur),
            "ledger_cost_eur": _serialize(self.ledger_cost_eur),
            "reference_realized_pnl_eur": _serialize(self.reference_realized_pnl_eur),
            "ledger_realized_pnl_eur": _serialize(self.ledger_realized_pnl_eur),
            "reference_average_cost_eur": _serialize(self.reference_average_cost_eur),
            "ledger_average_cost_eur": _serialize(self.ledger_average_cost_eur),
            "quantity_status": self.quantity_status,
            "cost_status": self.cost_status,
            "realized_pnl_status": self.realized_pnl_status,
            "average_cost_status": self.average_cost_status,
            "coverage": self.coverage,
            "differences": {key: {"imported": str(values[0]), "reference": str(values[1])} for key, values in self.differences.items()},
        }


def reconcile_preview_with_ledger(session: Session, preview: ImportPreview) -> LedgerReconciliation:
    if preview.errors:
        raise ValueError("La preview contiene righe non valide")
    reference_quantities: dict[str, Decimal] = {}
    reference_operations: dict[str, list[LedgerOperation]] = defaultdict(list)
    for row in preview.rows:
        key = f"{row.ticker}|{row.account_name}"
        reference_quantities[key] = reference_quantities.get(key, Decimal("0")) + _quantity_delta(row.kind, row.quantity)
        reference_operations[key].append(LedgerOperation(row.source_row, row.trade_date, row.source_row, row.kind, row.quantity, row.unit_price_eur))

    ledger_quantities: dict[str, Decimal] = {}
    ledger_operations: dict[str, list[LedgerOperation]] = defaultdict(list)
    statement = (
        select(Operation, Account.name, Instrument.ticker)
        .join(Account, Account.id == Operation.account_id)
        .join(Instrument, Instrument.id == Operation.instrument_id)
        .where(Operation.cancelled.is_(False))
    )
    for operation, account_name, ticker in session.execute(statement):
        key = f"{ticker}|{account_name}"
        ledger_quantities[key] = ledger_quantities.get(key, Decimal("0")) + _quantity_delta(operation.kind, Decimal(operation.quantity))
        ledger_operations[key].append(LedgerOperation(operation.id, operation.trade_date, operation.source_order, operation.kind, Decimal(operation.quantity), Decimal(operation.unit_price_eur), Decimal(operation.fee_eur) if operation.fee_eur is not None else None, Decimal(operation.dividend_eur) if operation.dividend_eur is not None else None))

    quantity_differences = _differences(ledger_quantities, reference_quantities, ReconciliationTolerance().quantity)
    cost_reference = _metric(reference_operations, "open_cost_eur")
    cost_ledger = _metric(ledger_operations, "open_cost_eur")
    pnl_reference = _metric(reference_operations, "realized_pnl_eur")
    pnl_ledger = _metric(ledger_operations, "realized_pnl_eur")
    average_reference = _average_cost(cost_reference, reference_quantities)
    average_ledger = _average_cost(cost_ledger, ledger_quantities)
    tolerance = ReconciliationTolerance()
    differences = dict(quantity_differences)
    differences.update({f"cost_eur|{key}": values for key, values in _differences(cost_ledger, cost_reference, tolerance.cost_eur).items()})
    differences.update({f"realized_pnl_eur|{key}": values for key, values in _differences(pnl_ledger, pnl_reference, tolerance.realized_pnl_eur).items()})
    average_differences = _differences(average_ledger, average_reference, tolerance.cost_eur)
    differences.update({f"average_cost_eur|{key}": values for key, values in average_differences.items()})
    dividend_coverage = "available" if any(operation.kind == "DIVIDEND" for operations in reference_operations.values() for operation in operations) or any(operation.kind == "DIVIDEND" for operations in ledger_operations.values() for operation in operations) else "not_comparable"
    return LedgerReconciliation(
        reference_quantities=reference_quantities,
        ledger_quantities=ledger_quantities,
        quantity_status="matched" if not quantity_differences else "mismatch",
        reference_cost_eur=cost_reference,
        ledger_cost_eur=cost_ledger,
        reference_realized_pnl_eur=pnl_reference,
        ledger_realized_pnl_eur=pnl_ledger,
        cost_status="matched" if not _differences(cost_ledger, cost_reference, tolerance.cost_eur) else "mismatch",
        realized_pnl_status="matched" if not _differences(pnl_ledger, pnl_reference, tolerance.realized_pnl_eur) else "mismatch",
        differences=differences,
        tolerance=tolerance,
        reference_average_cost_eur=average_reference,
        ledger_average_cost_eur=average_ledger,
        average_cost_status="matched" if not average_differences else "mismatch",
        coverage={"dividends": dividend_coverage, "benchmarks": "not_comparable"},
    )


def _quantity_delta(kind: str, quantity: Decimal) -> Decimal:
    if kind in {"BUY", "OPENING_BALANCE", "TRANSFER_IN", "SPLIT"}:
        return quantity
    if kind in {"SELL", "TRANSFER_OUT"}:
        return -quantity
    if kind == "ADJUSTMENT":
        return quantity
    return Decimal("0")


def _metric(groups: dict[str, list[LedgerOperation]], attribute: str) -> dict[str, Decimal]:
    values: dict[str, Decimal] = {}
    for key, operations in groups.items():
        snapshot = rebuild_position(operations)
        values[key] = getattr(snapshot, attribute) if attribute == "open_cost_eur" else snapshot.realized.pnl_eur
    return values


def _differences(actual: dict[str, Decimal], expected: dict[str, Decimal], tolerance: Decimal) -> dict[str, tuple[Decimal, Decimal]]:
    return {
        key: (actual.get(key, Decimal("0")), expected.get(key, Decimal("0")))
        for key in set(actual) | set(expected)
        if abs(actual.get(key, Decimal("0")) - expected.get(key, Decimal("0"))) > tolerance
    }


def _serialize(values: dict[str, Decimal]) -> dict[str, str]:
    return {key: str(value) for key, value in values.items()}


def _average_cost(costs: dict[str, Decimal], quantities: dict[str, Decimal]) -> dict[str, Decimal]:
    return {key: cost / quantities[key] for key, cost in costs.items() if quantities.get(key, Decimal("0")) != 0}
