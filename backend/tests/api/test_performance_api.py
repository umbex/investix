from datetime import datetime, timezone
from decimal import Decimal

from app.models import Benchmark, Instrument, Observation
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


def test_performance_api_filters_points_and_benchmarks_by_date(monkeypatch) -> None:
    client = client_with_database(monkeypatch)
    create_buy(client)
    session = client.app.state.session_factory()
    instrument = session.query(Instrument).filter_by(ticker="VWCE").one()
    session.add_all(
        [
            Observation(instrument_id=instrument.id, provider="fixture", price=Decimal("100"), raw_price=Decimal("100"), currency="EUR", fx_to_eur=Decimal("1"), observed_at=datetime(2026, 1, 2, tzinfo=timezone.utc)),
            Observation(instrument_id=instrument.id, provider="fixture", price=Decimal("105"), raw_price=Decimal("105"), currency="EUR", fx_to_eur=Decimal("1"), observed_at=datetime(2026, 1, 3, tzinfo=timezone.utc)),
            Observation(instrument_id=instrument.id, provider="fixture", price=Decimal("110"), raw_price=Decimal("110"), currency="EUR", fx_to_eur=Decimal("1"), observed_at=datetime(2026, 1, 4, tzinfo=timezone.utc)),
        ]
    )
    session.commit()

    response = client.get("/api/performance?date_from=2026-01-03&date_to=2026-01-04")

    assert response.status_code == 200
    assert [point["date"] for point in response.json()["points"]] == ["2026-01-03", "2026-01-04"]


def test_performance_csv_uses_the_same_date_filter(monkeypatch) -> None:
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

    response = client.get("/api/performance/export.csv?date_from=2026-01-03")

    assert response.status_code == 200
    lines = response.text.splitlines()
    assert lines[0] == "date,value_eur,external_flow_eur,cumulative_return"
    assert lines[1].startswith("2026-01-03,220")
    assert "2026-01-02" not in response.text


def test_performance_api_returns_active_price_return_benchmark_on_the_same_dates(monkeypatch) -> None:
    client = client_with_database(monkeypatch)
    create_buy(client)
    session = client.app.state.session_factory()
    portfolio_instrument = session.query(Instrument).filter_by(ticker="VWCE").one()
    benchmark_instrument = Instrument(ticker="QQQ", quote_symbol="QQQ", quote_venue="NASDAQ", quote_currency="USD")
    session.add(benchmark_instrument)
    session.flush()
    session.add(Benchmark(name="Nasdaq-100", ticker="QQQ", quote_symbol="QQQ", quote_venue="NASDAQ", quote_currency="USD", methodology="price_return", active=True))
    session.add_all(
        [
            Observation(instrument_id=portfolio_instrument.id, provider="fixture", price=Decimal("100"), raw_price=Decimal("100"), currency="EUR", fx_to_eur=Decimal("1"), observed_at=datetime(2026, 1, 2, tzinfo=timezone.utc)),
            Observation(instrument_id=portfolio_instrument.id, provider="fixture", price=Decimal("110"), raw_price=Decimal("110"), currency="EUR", fx_to_eur=Decimal("1"), observed_at=datetime(2026, 1, 3, tzinfo=timezone.utc)),
            Observation(instrument_id=benchmark_instrument.id, provider="fixture", price=Decimal("400"), raw_price=Decimal("500"), currency="USD", fx_to_eur=Decimal("0.8"), observed_at=datetime(2026, 1, 2, tzinfo=timezone.utc)),
            Observation(instrument_id=benchmark_instrument.id, provider="fixture", price=Decimal("440"), raw_price=Decimal("550"), currency="USD", fx_to_eur=Decimal("0.8"), observed_at=datetime(2026, 1, 3, tzinfo=timezone.utc)),
        ]
    )
    session.commit()

    response = client.get("/api/performance")

    assert response.status_code == 200
    payload = response.json()
    assert payload["benchmarks"] == [
        {
            "name": "Nasdaq-100",
            "ticker": "QQQ",
            "quote_currency": "USD",
            "methodology": "price_return",
            "points": [
                {"date": "2026-01-02", "return": "0"},
                {"date": "2026-01-03", "return": "0.1"},
            ],
        }
    ]


def test_benchmark_configuration_is_authenticated_and_updates_the_quote_catalog(monkeypatch) -> None:
    client = client_with_database(monkeypatch)

    response = client.put(
        "/api/benchmarks/QQQ",
        json={
            "name": "Nasdaq-100",
            "ticker": "QQQ",
            "quote_symbol": "QQQ",
            "quote_venue": "NASDAQ",
            "quote_currency": "USD",
            "methodology": "price_return",
            "active": True,
            "note": "Proxy ETF; dividendi esclusi.",
        },
    )

    assert response.status_code == 200
    assert response.json()["methodology"] == "price_return"
    assert client.get("/api/benchmarks").json()[0]["ticker"] == "QQQ"
    session = client.app.state.session_factory()
    assert session.query(Instrument).filter_by(ticker="QQQ").one().quote_currency == "USD"
