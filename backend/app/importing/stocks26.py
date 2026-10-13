import csv
import hashlib
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path


SUPPORTED_TYPES = {"Acquisto": "BUY", "Vendita": "SELL", "Saldo iniziale": "BUY"}


@dataclass(frozen=True)
class StagedRow:
    source_row: int
    trade_date: date
    account_name: str
    ticker: str
    kind: str
    quantity: Decimal
    unit_price_eur: Decimal
    quote_symbol: str
    quote_currency: str


@dataclass(frozen=True)
class ImportPreview:
    source_hash: str
    rows: list[StagedRow]
    errors: list[str]

    @property
    def valid_rows(self) -> int:
        return len(self.rows)


def preview_movimenti(source: Path) -> ImportPreview:
    raw = source.read_bytes()
    rows: list[StagedRow] = []
    errors: list[str] = []
    with source.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {"DATA", "CONTO", "TICKER", "TIPO", "QUANTITÀ", "PREZZO EUR", "SIMBOLO QUOTA", "VALUTA QUOTA"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            return ImportPreview(hashlib.sha256(raw).hexdigest(), [], ["Intestazioni MOVIMENTI non corrispondenti allo schema M:N"])
        for source_row, row in enumerate(reader, start=5):
            try:
                if row["TIPO"] not in SUPPORTED_TYPES:
                    raise ValueError(f"tipo non mappato: {row['TIPO']}")
                if any("#" in (row[key] or "") for key in ("QUANTITÀ", "PREZZO EUR")):
                    raise ValueError("formula o errore non importabile")
                quantity = Decimal(row["QUANTITÀ"])
                price = Decimal(row["PREZZO EUR"])
                if quantity <= 0 or price < 0 or not row["TICKER"] or not row["CONTO"]:
                    raise ValueError("riga incompleta o quantità/prezzo invalidi")
                rows.append(StagedRow(source_row, _parse_date(row["DATA"]), row["CONTO"], row["TICKER"].upper(), SUPPORTED_TYPES[row["TIPO"]], quantity, price, row["SIMBOLO QUOTA"], row["VALUTA QUOTA"].upper()))
            except (InvalidOperation, ValueError) as error:
                errors.append(f"Riga {source_row}: {error}")
    return ImportPreview(hashlib.sha256(raw).hexdigest(), rows, errors)


def _parse_date(value: str) -> date:
    for pattern in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, pattern).date()
        except ValueError:
            pass
    raise ValueError("data non valida")
