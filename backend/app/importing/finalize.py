from sqlalchemy import select
from sqlalchemy.orm import Session

from app.importing.stocks26 import ImportPreview
from app.models import ImportRow, ImportRun
from app.schemas.operations import OperationCreate
from app.services.operations import create_operation


class FinalizationError(ValueError):
    pass


def finalize_preview(session: Session, preview: ImportPreview) -> int:
    if preview.errors:
        raise FinalizationError("La preview contiene righe non valide e non può essere finalizzata")
    if session.scalar(select(ImportRun).where(ImportRun.source_hash == preview.source_hash)) is not None:
        raise FinalizationError("Questo file è già stato importato")
    run = ImportRun(source_hash=preview.source_hash)
    session.add(run)
    session.flush()
    for row in preview.rows:
        create_operation(session, OperationCreate(account_name=row.account_name, ticker=row.ticker, kind=row.kind, quantity=row.quantity, unit_price_eur=row.unit_price_eur, trade_date=row.trade_date, source_order=row.source_row), commit=False)
        session.add(ImportRow(import_run_id=run.id, source_row=row.source_row))
    session.commit()
    return run.id
