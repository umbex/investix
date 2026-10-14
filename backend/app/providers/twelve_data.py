"""Low-volume EOD adapter for Twelve Data's free Basic plan."""

import json
from collections.abc import Callable
from collections.abc import Iterable
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode
from urllib.request import urlopen

from app.providers.base import LiveQuote, MarketObservation, ProviderError, normalize_observation


class TwelveDataAdapter:
    provider_name = "twelve-data"

    def __init__(self, *, api_key: str, fx_to_eur: Callable[[datetime], Decimal] | None = None, download: Callable[[str], str] | None = None) -> None:
        if not api_key:
            raise ValueError("INVESTIX_TWELVE_DATA_API_KEY non configurata")
        self.api_key = api_key
        self._fx_to_eur = fx_to_eur
        self._download = download or _download

    def fetch_latest(self, symbol: str, *, ticker: str | None = None, exchange: str | None = None) -> MarketObservation:
        query = urlencode({"symbol": symbol, "interval": "1day", "outputsize": 1, "apikey": self.api_key, **({"exchange": exchange} if exchange else {})})
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
            observation = normalize_observation(provider=self.provider_name, ticker=ticker or symbol, observed_at=observed_at, raw_price=Decimal(value["close"]), currency=currency, fx_to_eur=fx_to_eur)
            return observation.__class__(**{**observation.__dict__, "source_symbol": symbol, "venue": meta.get("exchange"), "quote_unit": "share", "fx_provider": "ecb-reference" if currency != "EUR" else None})
        except (KeyError, IndexError, ValueError, InvalidOperation) as error:
            raise ProviderError(f"Risposta Twelve Data non valida: {error}") from error

    def fetch_live_quotes(self, symbols: list[str]) -> list[LiveQuote]:
        normalized = list(dict.fromkeys(symbol.strip() for symbol in symbols if symbol.strip()))
        if not normalized:
            return []
        query = urlencode({"symbol": ",".join(normalized), "apikey": self.api_key})
        try:
            payload = json.loads(self._download(f"https://api.twelvedata.com/quote?{query}"))
        except (OSError, json.JSONDecodeError) as error:
            raise ProviderError(f"Twelve Data non raggiungibile: {error}", retryable=True) from error
        if "code" in payload:
            message = str(payload.get("message", "errore provider"))
            retryable = "credit" in message.lower() or str(payload.get("code")) == "429"
            if retryable:
                raise ProviderError(f"Twelve Data: crediti o rate limit esauriti ({message})", retryable=True)
            raise ProviderError(f"Twelve Data: {message}", retryable=False)
        quotes: list[LiveQuote] = []
        for symbol in normalized:
            value = payload.get(symbol)
            if value is None:
                raise ProviderError(f"Twelve Data: simbolo non disponibile ({symbol})")
            if isinstance(value, dict) and "code" in value:
                message = str(value.get("message", "errore provider"))
                raise ProviderError(f"Twelve Data: simbolo non disponibile ({message})")
            try:
                currency = str(value.get("currency") or symbol.rsplit("/", 1)[-1] or "EUR").upper()
                observed_at = datetime.fromisoformat(str(value["datetime"]).replace(" ", "T")).replace(tzinfo=timezone.utc)
                price = Decimal(str(value.get("close") or value["price"]))
                change = value.get("percent_change")
                fx = Decimal("1") if currency == "EUR" else (self._fx_to_eur(observed_at) if self._fx_to_eur else None)
                quotes.append(LiveQuote(ticker=symbol, price=price, change_percent=Decimal(str(change)) if change not in (None, "") else None, observed_at=observed_at, currency=currency, price_eur=price * fx if fx else None, provider=self.provider_name, source_symbol=symbol, raw=value))
            except (KeyError, TypeError, ValueError, InvalidOperation) as error:
                raise ProviderError(f"Risposta Twelve Data non valida: {error}") from error
        return quotes

    def search_symbols(self, query: str) -> list[dict[str, str | None]]:
        normalized = query.strip()
        if not normalized:
            return []
        params = urlencode({"symbol": normalized, "apikey": self.api_key})
        try:
            payload = json.loads(self._download(f"https://api.twelvedata.com/symbol_search?{params}"))
        except (OSError, json.JSONDecodeError) as error:
            raise ProviderError(f"Twelve Data non raggiungibile: {error}", retryable=True) from error
        if "code" in payload:
            message = str(payload.get("message", "errore provider"))
            raise ProviderError(f"Twelve Data: {message}", retryable="credit" in message.lower() or str(payload.get("code")) == "429")
        return [
            {
                "symbol": str(item.get("symbol", "")),
                "name": str(item.get("instrument_name", "")),
                "exchange": str(item.get("exchange", "")),
                "currency": str(item.get("currency", "")),
                "type": str(item.get("type", "")),
            }
            for item in payload.get("data", [])
            if item.get("symbol")
        ]

    def fetch_history(self, symbol: str, *, ticker: str | None = None, start_date: date, end_date: date, exchange: str | None = None) -> Iterable[MarketObservation]:
        query = urlencode({"symbol": symbol, "interval": "1day", "start_date": start_date.isoformat(), "end_date": end_date.isoformat(), "outputsize": 5000, "apikey": self.api_key, **({"exchange": exchange} if exchange else {})})
        try:
            payload = json.loads(self._download(f"https://api.twelvedata.com/time_series?{query}"))
            if "code" in payload:
                message = str(payload.get("message", "errore provider"))
                retryable = "credit" in message.lower() or str(payload["code"]) == "429"
                raise ProviderError(f"Twelve Data: {message}", retryable=retryable)
            meta = payload["meta"]
            return [self._parse_observation(meta, value, symbol=symbol, ticker=ticker or symbol) for value in payload.get("values", [])]
        except ProviderError:
            raise
        except (OSError, json.JSONDecodeError) as error:
            raise ProviderError(f"Twelve Data non raggiungibile: {error}", retryable=True) from error
        except (KeyError, ValueError, InvalidOperation) as error:
            raise ProviderError(f"Risposta Twelve Data non valida: {error}") from error

    def _parse_observation(self, meta: dict, value: dict, *, symbol: str, ticker: str) -> MarketObservation:
        observed_at = datetime.fromisoformat(value["datetime"]).replace(tzinfo=timezone.utc)
        currency = meta["currency"].upper()
        if currency == "EUR":
            fx_to_eur = Decimal("1")
        elif self._fx_to_eur is None:
            raise ProviderError(f"Manca il cambio storico {currency}/EUR per {observed_at.date().isoformat()}")
        else:
            fx_to_eur = self._fx_to_eur(observed_at)
        observation = normalize_observation(provider=self.provider_name, ticker=ticker, observed_at=observed_at, raw_price=Decimal(value["close"]), currency=currency, fx_to_eur=fx_to_eur)
        return observation.__class__(**{**observation.__dict__, "source_symbol": symbol, "venue": meta.get("exchange"), "quote_unit": "share", "fx_provider": "ecb-reference" if currency != "EUR" else None})


def _download(url: str) -> str:
    try:
        with urlopen(url, timeout=20) as response:  # noqa: S310 - fixed provider endpoint
            return response.read().decode("utf-8")
    except OSError as error:
        raise ProviderError(f"Twelve Data non raggiungibile: {error}", retryable=True) from error
