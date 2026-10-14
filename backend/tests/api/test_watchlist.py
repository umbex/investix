from datetime import datetime, timezone
from decimal import Decimal

from app.models import Instrument, Observation
from tests.api.test_operations import client_with_database


def test_verified_watch_instrument_is_catalogued_and_included_in_quotes(monkeypatch) -> None:
    client = client_with_database(monkeypatch)

    response = client.put(
        "/api/instruments/watch/URTH",
        json={"quote_symbol": "URTH", "quote_venue": "NYSE", "quote_currency": "USD"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "ticker": "URTH",
        "quote_symbol": "URTH",
        "quote_venue": "NYSE",
        "quote_currency": "USD",
        "watch": True,
        "has_position": False,
    }
    assert client.get("/api/quotes?days=30").json()["items"][0]["ticker"] == "URTH"
    session = client.app.state.session_factory()
    instrument = session.query(Instrument).filter_by(ticker="URTH").one()
    session.add(Observation(instrument_id=instrument.id, provider="fixture", price=Decimal("100"), raw_price=Decimal("100"), currency="USD", fx_to_eur=Decimal("0.9"), observed_at=datetime(2026, 1, 2, tzinfo=timezone.utc)))
    session.commit()
    session.close()

    assert client.get("/api/instruments/catalog").json()[0]["watch"] is True
    assert client.get("/api/quotes?days=30").json()["items"][0]["ticker"] == "URTH"


def test_watchlist_rejects_more_than_five_instruments(monkeypatch) -> None:
    client = client_with_database(monkeypatch)
    for index in range(5):
        assert client.put(f"/api/instruments/watch/W{index}", json={"quote_symbol": f"W{index}", "quote_venue": "NASDAQ", "quote_currency": "USD"}).status_code == 200

    response = client.put("/api/instruments/watch/W5", json={"quote_symbol": "W5", "quote_venue": "NASDAQ", "quote_currency": "USD"})

    assert response.status_code == 422


def test_activating_a_benchmark_deactivates_the_previous_one(monkeypatch) -> None:
    client = client_with_database(monkeypatch)
    payload = {"name": "Nasdaq-100", "ticker": "QQQ", "quote_symbol": "QQQ", "quote_venue": "NASDAQ", "quote_currency": "USD", "methodology": "price_return", "active": True}
    assert client.put("/api/benchmarks/QQQ", json=payload).status_code == 200
    payload.update({"name": "MSCI World", "ticker": "URTH", "quote_symbol": "URTH", "quote_venue": "NYSE"})
    assert client.put("/api/benchmarks/URTH", json=payload).status_code == 200

    benchmarks = client.get("/api/benchmarks").json()

    assert [item["ticker"] for item in benchmarks if item["active"]] == ["URTH"]
