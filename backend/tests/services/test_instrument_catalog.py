from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models import Base, Instrument
from app.services.instrument_catalog import configure_instrument


def test_catalog_persists_isin_and_preferred_eur_listing() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        instrument = configure_instrument(
            session,
            ticker="EQQQ",
            isin="IE0032077012",
            quote_symbol="EQQQ.MI",
            quote_venue="Borsa Italiana",
            quote_currency="EUR",
        )

        assert instrument.isin == "IE0032077012"
        assert instrument.quote_symbol == "EQQQ.MI"
        assert instrument.quote_venue == "Borsa Italiana"
        assert instrument.quote_currency == "EUR"
