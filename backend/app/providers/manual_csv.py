import csv
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

from app.providers.base import MarketObservation, ProviderError, normalize_observation


class ManualCsvAdapter:
    """A deterministic local provider for backfills and unsupported symbols."""

    provider_name = "manual-csv"

    def __init__(self, source: Path) -> None:
        self.source = source

    def fetch(self, ticker: str) -> MarketObservation:
        try:
            with self.source.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
        except OSError as error:
            raise ProviderError(f"CSV non disponibile: {error}") from error
        matches = [row for row in rows if row.get("ticker", "").upper() == ticker.upper()]
        if not matches:
            raise ProviderError(f"Simbolo {ticker} non trovato nel CSV")
        row = matches[-1]
        try:
            observed_at = datetime.fromisoformat(row["date"]).replace(tzinfo=timezone.utc)
            return normalize_observation(
                provider=self.provider_name,
                ticker=ticker,
                observed_at=observed_at,
                raw_price=Decimal(row["price"]),
                currency=row["currency"],
                fx_to_eur=Decimal(row["fx_to_eur"]),
            )
        except (KeyError, ValueError, InvalidOperation) as error:
            raise ProviderError(f"Riga CSV non valida: {error}") from error
