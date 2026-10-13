from decimal import Decimal
from dataclasses import dataclass


class ReconciliationError(ValueError):
    pass


@dataclass(frozen=True)
class ReconciliationTolerance:
    quantity: Decimal = Decimal("0")
    cost_eur: Decimal = Decimal("0.01")
    realized_pnl_eur: Decimal = Decimal("0.01")


@dataclass(frozen=True)
class ReconciliationReport:
    passed: bool
    quantity_tolerance: Decimal
    differences: dict[str, tuple[Decimal, Decimal]]


def reconciliation_report(imported: dict[str, Decimal], reference: dict[str, Decimal], *, tolerance: ReconciliationTolerance = ReconciliationTolerance()) -> ReconciliationReport:
    differences = {
        key: (imported.get(key, Decimal("0")), reference.get(key, Decimal("0")))
        for key in set(imported) | set(reference)
        if abs(imported.get(key, Decimal("0")) - reference.get(key, Decimal("0"))) > tolerance.quantity
    }
    return ReconciliationReport(not differences, tolerance.quantity, differences)


def reconcile_quantities(imported: dict[str, Decimal], reference: dict[str, Decimal], *, tolerance: Decimal = Decimal("0")) -> None:
    differences = {
        key: (imported.get(key, Decimal("0")), reference.get(key, Decimal("0")))
        for key in set(imported) | set(reference)
        if abs(imported.get(key, Decimal("0")) - reference.get(key, Decimal("0"))) > tolerance
    }
    if differences:
        detail = ", ".join(f"{key}: importato {actual}, riferimento {expected}" for key, (actual, expected) in sorted(differences.items()))
        raise ReconciliationError(f"Riconciliazione quantità non superata: {detail}")
