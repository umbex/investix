"""Low-volume EOD adapter for Twelve Data's free Basic plan."""

import json
from collections.abc import Callable
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode
from urllib.request import urlopen

from app.providers.base import MarketObservation, ProviderError, normalize_observation


class TwelveDataAdapter:
    provider_name = "twelve-data"

    def __init__(self, *, api_key: str, fx_to_eur: Callable[[datetime], Decimal] | None = None, download: Callable[[str], str] | None = None) -> None:
        if not api_key:
            raise ValueError("INVESTIX_TWELVE_DATA_API_KEY non configurata")
        self.api_key = api_key
        self._fx_to_eur = fx_to_eur
        self._download = download or _download

    def fetch_latest(self, symbol: str, *, ticker: str | None = None) -> MarketObservation:
        query = urlencode({"symbol": symbol, "interval": "1day", "outputsize": 1, "apikey": self.api_key})
        try:
            payload = json.loads(self._download(f"https://api.twelvedata.com/time_series?{query}"))
        except (OSError, json.JSONDecodeError) as error:
            raise ProviderError(f"Twelve Data non raggiungibile: {error}", retryable=True) from error
        if "code" in payload:
            message = str(payload.get("message", "errore provider"))
            if "credit" in message.lower() or str(payload["code"]) == "429":
                raise ProviderError("Twelve Data: crediti o rate limit esauriti", retryable=True)
            raise ProviderError(f"Twelve Data: simbolo non disponibile ({message})")
        try:
            meta, value = payload["meta"], payload["values"][0]
            observed_at = datetime.fromisoformat(value["datetime"]).replace(tzinfo=timezone.utc)
            currency = meta["currency"].upper()
            if currency == "EUR":
                fx_to_eur = Decimal("1")
            elif self._fx_to_eur is None:
                raise ProviderError(f"Manca il cambio storico {currency}/EUR per {observed_at.date().isoformat()}")
            else:
                fx_to_eur = self._fx_to_eur(observed_at)
            return normalize_observation(provider=self.provider_name, ticker=ticker or symbol, observed_at=observed_at, raw_price=Decimal(value["close"]), currency=currency, fx_to_eur=fx_to_eur)
        except (KeyError, IndexError, ValueError, InvalidOperation) as error:
            raise ProviderError(f"Risposta Twelve Data non valida: {error}") from error


def _download(url: str) -> str:
    try:
        with urlopen(url, timeout=20) as response:  # noqa: S310 - fixed provider endpoint
            return response.read().decode("utf-8")
    except OSError as error:
        raise ProviderError(f"Twelve Data non raggiungibile: {error}", retryable=True) from error
