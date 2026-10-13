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
    assert report.reference_quantities == {"VWCE|Directa": Decimal("2")}
    assert report.ledger_quantities == {"VWCE|Directa": Decimal("2")}
