"""ECB reference-rate adapter for low-volume USD/EUR enrichment."""

import csv
from collections.abc import Callable
from datetime import date
from decimal import Decimal, InvalidOperation
from io import StringIO
from urllib.parse import urlencode
from urllib.request import urlopen

from app.providers.base import ProviderError

ECB_USD_EUR_SERIES = "D.USD.EUR.SP00.A"
ECB_DATA_URL = "https://data-api.ecb.europa.eu/service/data/EXR/"


class EcbUsdEurAdapter:
    """Return ECB USD/EUR reference rates normalized as EUR per USD."""

    provider_name = "ecb-reference"

    def __init__(self, *, download: Callable[[str], str] | None = None) -> None:
        self._download = download or _download

    def fetch_rates(self, start: date, end: date) -> dict[date, Decimal]:
        if end < start:
            raise ProviderError("Intervallo ECB non valido")
        query = urlencode({"startPeriod": start.isoformat(), "endPeriod": end.isoformat(), "format": "csvdata"})
        payload = self._download(f"{ECB_DATA_URL}{ECB_USD_EUR_SERIES}?{query}")
        rates: dict[date, Decimal] = {}
        try:
            for row in csv.DictReader(StringIO(payload)):
                period = date.fromisoformat(row["TIME_PERIOD"])
                usd_per_eur = Decimal(row["OBS_VALUE"])
                if usd_per_eur <= 0:
                    raise ValueError("valore non positivo")
                rates[period] = Decimal("1") / usd_per_eur
        except (KeyError, TypeError, ValueError, InvalidOperation) as error:
            raise ProviderError(f"Risposta ECB non valida: {error}") from error
        if not rates:
            raise ProviderError("ECB non ha restituito cambi USD/EUR per l'intervallo richiesto")
        return rates

    @staticmethod
    def rate_for(target: date, rates: dict[date, Decimal]) -> Decimal:
        prior_dates = [observed_on for observed_on in rates if observed_on <= target]
        if not prior_dates:
            raise ProviderError(f"ECB non ha un cambio USD/EUR precedente al {target.isoformat()}")
        return rates[max(prior_dates)]


def _download(url: str) -> str:
    try:
        with urlopen(url, timeout=20) as response:  # noqa: S310 - fixed official ECB endpoint
            return response.read().decode("utf-8")
    except OSError as error:
        raise ProviderError(f"ECB non raggiungibile: {error}", retryable=True) from error
