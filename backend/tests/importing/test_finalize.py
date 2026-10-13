from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
import pytest

from app.importing.finalize import FinalizationError, finalize_preview
from app.importing.stocks26 import ImportPreview, StagedRow
from app.models import Base, Operation


def test_finalization_is_atomic_and_idempotent() -> None:
    from datetime import date
    from decimal import Decimal
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    preview = ImportPreview("hash", [StagedRow(5, date(2026, 1, 2), "Directa", "VWCE", "BUY", Decimal("2"), Decimal("100"), "VWCE", "EUR")], [])
    with Session(engine) as session:
        finalize_preview(session, preview)
        assert len(list(session.scalars(select(Operation)))) == 1
        with pytest.raises(FinalizationError, match="già"):
            finalize_preview(session, preview)
