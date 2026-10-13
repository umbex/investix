from decimal import Decimal

import pytest

from app.importing.reconcile import ReconciliationError, reconcile_quantities
from app.importing.reconcile import ReconciliationTolerance, reconciliation_report


def test_reconciliation_accepts_equal_quantities() -> None:
    reconcile_quantities({"VWCE|Directa": Decimal("2")}, {"VWCE|Directa": Decimal("2")})


def test_reconciliation_blocks_unexplained_difference() -> None:
    with pytest.raises(ReconciliationError, match="VWCE\\|Directa"):
        reconcile_quantities({"VWCE|Directa": Decimal("2")}, {"VWCE|Directa": Decimal("1")})


def test_reconciliation_report_exposes_tolerance_and_explainable_mismatch() -> None:
    report = reconciliation_report(
        {"VWCE|Directa": Decimal("2")},
        {"VWCE|Directa": Decimal("1.99")},
        tolerance=ReconciliationTolerance(quantity=Decimal("0.01")),
    )

    assert report.passed is True
    assert report.quantity_tolerance == Decimal("0.01")
