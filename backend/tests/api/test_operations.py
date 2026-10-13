from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_session
from app.main import create_app
from app.models import Base
from app.settings import get_settings


def client_with_database(monkeypatch) -> TestClient:
    monkeypatch.setenv("INVESTIX_ADMIN_PASSWORD", "test-password")
    monkeypatch.setenv("INVESTIX_SESSION_SECRET", "test-session-secret-with-at-least-32chars")
    get_settings.cache_clear()
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    app = create_app()
    app.state.session_factory = sessions

    def session_override():
        with sessions() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    client = TestClient(app)
    assert client.post("/api/auth/login", json={"username": "investix", "password": "test-password"}).status_code == 204
    return client


def create_buy(client: TestClient, *, order: int = 1) -> dict:
    response = client.post(
        "/api/operations",
        json={
            "account_name": "Directa",
            "ticker": "VWCE",
            "kind": "BUY",
            "quantity": "2",
            "unit_price_eur": "100",
            "trade_date": "2026-01-02",
            "source_order": order,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_authenticated_user_can_create_and_filter_operations(monkeypatch) -> None:
    client = client_with_database(monkeypatch)
    created = create_buy(client)

    response = client.get("/api/operations?ticker=VWCE")

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["id"] == created["id"]


def test_revision_creates_a_new_audited_ledger_entry(monkeypatch) -> None:
    client = client_with_database(monkeypatch)
    original = create_buy(client)

    response = client.post(
        f"/api/operations/{original['id']}/revise",
        json={"reason": "Prezzo corretto", "unit_price_eur": "90"},
    )

    assert response.status_code == 201
    revision = response.json()
    assert revision["id"] != original["id"]
    assert revision["unit_price_eur"] == "90.0000000000"
    active = client.get("/api/operations").json()
    assert active["total"] == 1
    assert active["items"][0]["id"] == revision["id"]


def test_cancel_is_audited_and_validation_rejects_invalid_sale(monkeypatch) -> None:
    client = client_with_database(monkeypatch)
    created = create_buy(client)

    cancelled = client.post(f"/api/operations/{created['id']}/cancel", json={"reason": "Duplicato"})
    invalid = client.post(
        "/api/operations",
        json={
            "account_name": "Directa",
            "ticker": "VWCE",
            "kind": "SELL",
            "quantity": "-1",
            "unit_price_eur": "100",
            "trade_date": str(date(2026, 1, 3)),
            "source_order": 2,
        },
    )

    assert cancelled.status_code == 204
    assert client.get("/api/operations").json()["total"] == 0
    assert invalid.status_code == 422


def test_portfolio_summary_is_derived_from_the_authenticated_ledger(monkeypatch) -> None:
    client = client_with_database(monkeypatch)
    create_buy(client)

    response = client.get("/api/portfolio")

    assert response.status_code == 200
    assert response.json()["valuation_status"] == "unavailable_without_observation"
    position = response.json()["positions"][0]
    assert position["ticker"] == "VWCE"
    assert Decimal(position["quantity"]) == Decimal("2")
    assert Decimal(position["open_cost_eur"]) == Decimal("200")
    assert Decimal(position["realized_pnl_eur"]) == Decimal("0")


def test_operations_preserve_context_and_support_explicit_operational_kinds(monkeypatch) -> None:
    client = client_with_database(monkeypatch)

    opening = client.post(
        "/api/operations",
        json={
            "account_name": "Directa",
            "ticker": "EQQQ",
            "kind": "OPENING_BALANCE",
            "quantity": "4",
            "unit_price_eur": "123.45",
            "original_unit_price": "101.2",
            "original_currency": "GBP",
            "trade_date": "2026-01-02",
            "settlement_date": "2026-01-06",
            "source_order": 1,
            "note": "Saldo iniziale ricostruito",
            "is_approximate": True,
        },
    )
    transferred = client.post(
        "/api/operations",
        json={
            "account_name": "Directa",
            "ticker": "EQQQ",
            "kind": "TRANSFER_OUT",
            "quantity": "1",
            "unit_price_eur": "123.45",
            "trade_date": "2026-01-07",
            "source_order": 2,
        },
    )
    adjusted = client.post(
        "/api/operations",
        json={
            "account_name": "Directa",
            "ticker": "EQQQ",
            "kind": "ADJUSTMENT",
            "quantity": "-0.5",
            "unit_price_eur": "0",
            "trade_date": "2026-01-08",
            "source_order": 3,
        },
    )

    assert opening.status_code == 201
    assert transferred.status_code == 201
    assert adjusted.status_code == 201
    item = client.get("/api/operations").json()["items"][0]
    assert item["kind"] == "OPENING_BALANCE"
    assert item["original_unit_price"] == "101.2000000000"
    assert item["original_currency"] == "GBP"
    assert item["settlement_date"] == "2026-01-06"
    assert item["note"] == "Saldo iniziale ricostruito"
    assert item["is_approximate"] is True
