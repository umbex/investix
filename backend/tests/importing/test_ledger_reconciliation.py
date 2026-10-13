from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.importing.ledger_reconciliation import reconcile_preview_with_ledger
from app.importing.stocks26 import ImportPreview, StagedRow
from app.models import Base
from app.schemas.operations import OperationCreate
from app.services.operations import create_operation


def test_reconciliation_reports_matching_quantity_and_historical_coverage() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    preview = ImportPreview("source", [StagedRow(5, date(2026, 1, 2), "Directa", "VWCE", "BUY", Decimal("2"), Decimal("100"), "VWCE", "EUR")], [])
    with Session(engine) as session:
        create_operation(session, OperationCreate(account_name="Directa", ticker="VWCE", kind="BUY", quantity=Decimal("2"), unit_price_eur=Decimal("100"), trade_date=date(2026, 1, 2), source_order=5))

        report = reconcile_preview_with_ledger(session, preview)

    assert report.quantity_status == "matched"
    assert report.cost_status == "matched"
    assert report.realized_pnl_status == "matched"
    assert report.passed is True
    assert report.reference_quantities == {"VWCE|Directa": Decimal("2")}
    assert report.ledger_quantities == {"VWCE|Directa": Decimal("2")}


def test_reconciliation_reports_realized_pnl_difference() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    preview = ImportPreview("source", [
        StagedRow(5, date(2026, 1, 2), "Directa", "VWCE", "BUY", Decimal("2"), Decimal("100"), "VWCE", "EUR"),
        StagedRow(6, date(2026, 1, 3), "Directa", "VWCE", "SELL", Decimal("1"), Decimal("120"), "VWCE", "EUR"),
    ], [])
    with Session(engine) as session:
        create_operation(session, OperationCreate(account_name="Directa", ticker="VWCE", kind="BUY", quantity=Decimal("2"), unit_price_eur=Decimal("100"), trade_date=date(2026, 1, 2), source_order=5))
        create_operation(session, OperationCreate(account_name="Directa", ticker="VWCE", kind="SELL", quantity=Decimal("1"), unit_price_eur=Decimal("110"), trade_date=date(2026, 1, 3), source_order=6))

        report = reconcile_preview_with_ledger(session, preview)

    assert report.passed is False
    assert report.realized_pnl_status == "mismatch"
    assert "realized_pnl_eur|VWCE|Directa" in report.differences
