from fastapi.testclient import TestClient

from app.main import create_app
from app.settings import get_settings


def test_authenticated_preview_reports_valid_rows(monkeypatch) -> None:
    monkeypatch.setenv("INVESTIX_ADMIN_PASSWORD", "test-password")
    monkeypatch.setenv("INVESTIX_SESSION_SECRET", "test-session-secret-with-at-least-32chars")
    get_settings.cache_clear()
    client = TestClient(create_app())
    client.post("/api/auth/login", json={"username": "investix", "password": "test-password"})
    csv = "DATA,CONTO,TICKER,ISIN,TIPO,QUANTITÀ,PREZZO EUR,COMMISSIONI EUR,IMPORTO MOVIMENTO EUR,CONTROVALORE EUR,FLUSSO OPERAZIONE EUR,NOTE,SIMBOLO QUOTA,VALUTA QUOTA\n02/01/2026,Directa,VWCE,,Acquisto,2,100,,,,,,VWCE,EUR\n"

    response = client.post("/api/imports/stocks26/preview", json={"csv": csv})

    assert response.status_code == 200
    assert response.json()["valid_rows"] == 1
    assert response.json()["errors"] == []
