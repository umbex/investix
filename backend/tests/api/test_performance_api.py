from datetime import datetime, timezone
from decimal import Decimal

from app.models import Instrument, Observation
from tests.api.test_operations import client_with_database, create_buy


def test_performance_api_returns_daily_series_and_twr(monkeypatch) -> None:
    client = client_with_database(monkeypatch)
    create_buy(client)
    session = client.app.state.session_factory()
    instrument = session.query(Instrument).filter_by(ticker="VWCE").one()
    session.add_all(
        [
            Observation(instrument_id=instrument.id, provider="fixture", price=Decimal("100"), raw_price=Decimal("100"), currency="EUR", fx_to_eur=Decimal("1"), observed_at=datetime(2026, 1, 2, tzinfo=timezone.utc)),
            Observation(instrument_id=instrument.id, provider="fixture", price=Decimal("110"), raw_price=Decimal("110"), currency="EUR", fx_to_eur=Decimal("1"), observed_at=datetime(2026, 1, 3, tzinfo=timezone.utc)),
        ]
    )
    session.commit()

    response = client.get("/api/performance")

    assert response.status_code == 200
    payload = response.json()
    assert [point["date"] for point in payload["points"]] == ["2026-01-02", "2026-01-03"]
    assert Decimal(payload["total_return"]) == Decimal("0.1")
