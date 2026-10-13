from decimal import Decimal

import pytest

from app.importing.reconcile import ReconciliationError, reconcile_quantities


def test_reconciliation_accepts_equal_quantities() -> None:
    reconcile_quantities({"VWCE|Directa": Decimal("2")}, {"VWCE|Directa": Decimal("2")})


def test_reconciliation_blocks_unexplained_difference() -> None:
    with pytest.raises(ReconciliationError, match="VWCE\\|Directa"):
        reconcile_quantities({"VWCE|Directa": Decimal("2")}, {"VWCE|Directa": Decimal("1")})
