from pathlib import Path
from decimal import Decimal

from app.importing.stocks26 import preview_movimenti


HEADER = "DATA,CONTO,TICKER,ISIN,TIPO,QUANTITÀ,PREZZO EUR,COMMISSIONI EUR,IMPORTO MOVIMENTO EUR,CONTROVALORE EUR,FLUSSO OPERAZIONE EUR,NOTE,SIMBOLO QUOTA,VALUTA QUOTA\n"


def test_import_uses_actual_m_n_quote_headers_and_is_idempotent(tmp_path: Path) -> None:
    export = tmp_path / "movimenti.csv"
    export.write_text(HEADER + "2026-01-02,Directa,VWCE,,Acquisto,2,100,,,,,,VWCE,EUR\n")

    preview = preview_movimenti(export)

    assert preview.valid_rows == 1
    assert preview.rows[0].quote_symbol == "VWCE"
    assert preview.rows[0].quote_currency == "EUR"
    assert preview.rows[0].account_name == "Directa"
    assert preview.source_hash == preview_movimenti(export).source_hash


def test_import_blocks_unknown_type_and_formula_error(tmp_path: Path) -> None:
    export = tmp_path / "movimenti.csv"
    export.write_text(HEADER + "2026-01-02,Directa,VWCE,,Mistero,2,#N/D,,,,,,,EUR\n")

    preview = preview_movimenti(export)

    assert preview.valid_rows == 0
    assert len(preview.errors) == 1


def test_import_accepts_italian_date_format(tmp_path: Path) -> None:
    export = tmp_path / "movimenti.csv"
    export.write_text(HEADER + "02/01/2026,Directa,VWCE,,Acquisto,2,100,,,,,,VWCE,EUR\n")

    assert preview_movimenti(export).rows[0].trade_date.isoformat() == "2026-01-02"


def test_import_accepts_italian_quantity_and_eur_price(tmp_path: Path) -> None:
    export = tmp_path / "movimenti.csv"
    export.write_text(HEADER + "02/01/2026,Directa,VWCE,,Acquisto,80,00,€ 634,42,,,,,,VWCE,EUR\n")

    # CSV quoting keeps the Italian comma values inside their fields.
    export.write_text(HEADER + '02/01/2026,Directa,VWCE,,Acquisto,"80,00","€ 634,42",,,,,,VWCE,EUR\n')
    row = preview_movimenti(export).rows[0]
    assert row.quantity == Decimal("80")
    assert row.unit_price_eur == Decimal("634.42")
