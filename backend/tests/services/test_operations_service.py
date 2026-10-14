from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models import Base, Instrument
from app.schemas.operations import OperationCreate
from app.services.operations import create_operation


def test_create_operation_persists_selected_provider_listing() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        operation = create_operation(
            session,
            OperationCreate(
                account_name="Demo",
                ticker="AAPL",
                kind="BUY",
                quantity=Decimal("1"),
                unit_price_eur=Decimal("100"),
                trade_date=date(2026, 10, 14),
                source_order=0,
                quote_symbol="AAPL",
                quote_venue="NASDAQ",
                quote_currency="USD",
            ),
        )

        instrument = session.get(Instrument, operation.instrument_id)
        assert instrument is not None
        assert instrument.quote_symbol == "AAPL"
        assert instrument.quote_venue == "NASDAQ"
        assert instrument.quote_currency == "USD"
