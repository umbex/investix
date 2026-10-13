import csv
import hashlib
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path


SUPPORTED_TYPES = {"Acquisto": "BUY", "Vendita": "SELL", "Saldo iniziale": "OPENING_BALANCE", "Trasferimento in entrata": "TRANSFER_IN", "Trasferimento in uscita": "TRANSFER_OUT", "Rettifica": "ADJUSTMENT"}


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
    note: str | None = None
    original_currency: str | None = None


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
        if not reader.fieldnames:
            return ImportPreview(hashlib.sha256(raw).hexdigest(), [], ["Intestazioni MOVIMENTI non corrispondenti allo schema M:N"])
        headers = {header.upper(): header for header in reader.fieldnames}
        if not required.issubset(headers):
            return ImportPreview(hashlib.sha256(raw).hexdigest(), [], ["Intestazioni MOVIMENTI non corrispondenti allo schema M:N"])
        for source_row, row in enumerate(reader, start=5):
            try:
                values = {key: row[header] or "" for key, header in headers.items()}
                if values["TIPO"] not in SUPPORTED_TYPES:
                    raise ValueError(f"tipo non mappato: {values['TIPO']}")
                if any("#" in values[key] for key in ("QUANTITÀ", "PREZZO EUR")):
                    raise ValueError("formula o errore non importabile")
                quantity = _parse_decimal(values["QUANTITÀ"])
                price = _parse_decimal(values["PREZZO EUR"])
                if (quantity <= 0 and values["TIPO"] != "Rettifica") or price < 0 or not values["TICKER"] or not values["CONTO"]:
                    raise ValueError("riga incompleta o quantità/prezzo invalidi")
                rows.append(StagedRow(source_row, _parse_date(values["DATA"]), values["CONTO"], values["TICKER"].upper(), SUPPORTED_TYPES[values["TIPO"]], quantity, price, values["SIMBOLO QUOTA"], values["VALUTA QUOTA"].upper(), values.get("NOTE") or None, values["VALUTA QUOTA"].upper() or None))
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


def _parse_decimal(value: str) -> Decimal:
    normalized = value.replace("€", "").replace("\u00a0", "").strip().replace(".", "").replace(",", ".")
    return Decimal(normalized)
