from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select

from app.models import Instrument, Observation
from tests.api.test_operations import client_with_database, create_buy


def test_quotes_returns_latest_change_and_range_filtered_history(monkeypatch) -> None:
    client = client_with_database(monkeypatch)
    create_buy(client)
    sessions = client.app.state.session_factory
    with sessions() as session:
        instrument = session.scalar(select(Instrument).where(Instrument.ticker == "VWCE"))
        assert instrument is not None
        instrument.quote_symbol = "VWCE"
        instrument.quote_venue = "XETRA"
        session.commit()
        session.add_all([
            Observation(instrument_id=instrument.id, provider="test", price=Decimal("100"), raw_price=Decimal("100"), observed_at=datetime(2026, 1, 1, tzinfo=timezone.utc)),
            Observation(instrument_id=instrument.id, provider="test", price=Decimal("105"), raw_price=Decimal("105"), observed_at=datetime(2026, 1, 2, tzinfo=timezone.utc)),
            Observation(instrument_id=instrument.id, provider="test", price=Decimal("110"), raw_price=Decimal("110"), observed_at=datetime(2026, 5, 1, tzinfo=timezone.utc)),
        ])
        session.commit()

    response = client.get("/api/quotes?days=119")

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["ticker"] == "VWCE"
    assert Decimal(item["price_eur"]) == Decimal("110")
    assert Decimal(item["change_percent"]) == Decimal("4.7619047619")
    assert [point["price_eur"] for point in item["points"]] == ["105.0000000000", "110.0000000000"]


def test_dashboard_summary_exposes_account_breakdown_and_unavailable_valuation(monkeypatch) -> None:
    client = client_with_database(monkeypatch)
    create_buy(client)
    with client.app.state.session_factory() as session:
        instrument = session.scalar(select(Instrument).where(Instrument.ticker == "VWCE"))
        assert instrument is not None
        instrument.quote_symbol = "VWCE"
        instrument.quote_venue = "XETRA"
        session.commit()
    response = client.post(
        "/api/operations",
        json={
            "account_name": "Fineco",
            "ticker": "VWCE",
            "kind": "BUY",
            "quantity": "1",
            "unit_price_eur": "120",
            "trade_date": "2026-01-03",
            "source_order": 2,
        },
    )
    assert response.status_code == 201

    summary = client.get("/api/portfolio").json()

    assert summary["valuation_status"] == "unavailable_without_observation"
    assert Decimal(summary["kpis"]["open_cost_eur"]) == Decimal("320")
    assert summary["kpis"]["market_value_eur"] is None
    position = summary["positions"][0]
    assert Decimal(position["quantity"]) == Decimal("3")
    assert {item["name"] for item in position["accounts"]} == {"Directa", "Fineco"}
    assert position["market_data_status"] == "missing"
    assert position["market_data_provider"] is None
    assert position["market_data_venue"] == "XETRA"
    assert summary["allocations"][0]["weight"] is None
    assert {item["account"] for item in summary["allocations"][0]["accounts"]} == {"Directa", "Fineco"}
    assert {item["account"] for item in summary["account_allocations"]} == {"Directa", "Fineco"}


def test_allocation_accounts_stay_bound_to_each_ticker(monkeypatch) -> None:
    client = client_with_database(monkeypatch)
    create_buy(client)
    response = client.post(
        "/api/operations",
        json={
            "account_name": "Fineco",
            "ticker": "EQQQ",
            "kind": "BUY",
            "quantity": "1",
            "unit_price_eur": "50",
            "trade_date": "2026-01-03",
            "source_order": 2,
        },
    )
    assert response.status_code == 201

    allocations = {item["ticker"]: item for item in client.get("/api/portfolio").json()["allocations"]}

    assert [item["account"] for item in allocations["VWCE"]["accounts"]] == ["Directa"]
    assert [item["account"] for item in allocations["EQQQ"]["accounts"]] == ["Fineco"]


def test_portfolio_csv_uses_same_filtered_positions(monkeypatch) -> None:
    client = client_with_database(monkeypatch)
    create_buy(client)

    response = client.get("/api/portfolio/export.csv?ticker=VWCE")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "ticker,quantity,open_cost_eur" in response.text
    assert "VWCE,2.0000000000,200.0000000000" in response.text


def test_portfolio_account_filter_limits_positions_and_allocation(monkeypatch) -> None:
    client = client_with_database(monkeypatch)
    create_buy(client)
    response = client.post(
        "/api/operations",
        json={
            "account_name": "Fineco",
            "ticker": "VWCE",
            "kind": "BUY",
            "quantity": "1",
            "unit_price_eur": "120",
            "trade_date": "2026-01-03",
            "source_order": 2,
        },
    )
    assert response.status_code == 201

    summary = client.get("/api/portfolio?account=Fineco").json()

    assert summary["positions"][0]["quantity"] == "1.0000000000"
    assert summary["account_allocations"][0]["account"] == "Fineco"
    assert Decimal(summary["account_allocations"][0]["open_cost_eur"]) == Decimal("120")
    assert Decimal(summary["account_allocations"][0]["weight"]) == Decimal("1")
