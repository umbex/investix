from sqlalchemy import select
from sqlalchemy.orm import Session

from app.importing.stocks26 import ImportPreview
from app.importing.reconcile import ReconciliationReport
from app.models import ImportRow, ImportRun
from app.schemas.operations import OperationCreate
from app.services.operations import create_operation


class FinalizationError(ValueError):
    pass


def finalize_preview(session: Session, preview: ImportPreview, *, reconciliation: ReconciliationReport | None = None) -> int:
    if preview.errors:
        raise FinalizationError("La preview contiene righe non valide e non può essere finalizzata")
    if reconciliation is not None and not reconciliation.passed:
        raise FinalizationError("Riconciliazione non superata: la finalizzazione è bloccata")
    if session.scalar(select(ImportRun).where(ImportRun.source_hash == preview.source_hash)) is not None:
        raise FinalizationError("Questo file è già stato importato")
    run = ImportRun(source_hash=preview.source_hash)
    session.add(run)
    session.flush()
    for row in preview.rows:
        create_operation(session, OperationCreate(account_name=row.account_name, ticker=row.ticker, kind=row.kind, quantity=row.quantity, unit_price_eur=row.unit_price_eur, original_unit_price=row.unit_price_eur, original_currency=row.original_currency, note=row.note, is_approximate=row.kind == "OPENING_BALANCE" and bool(row.note), trade_date=row.trade_date, source_order=row.source_row), commit=False)
        session.add(ImportRow(import_run_id=run.id, source_row=row.source_row))
    session.commit()
    return run.id
