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


def test_import_accepts_actual_title_case_headers(tmp_path: Path) -> None:
    export = tmp_path / "movimenti.csv"
    header = "Data,Conto,Ticker,ISIN,Tipo,Quantità,Prezzo EUR,Commissioni EUR,Importo movimento EUR,Controvalore EUR,Flusso operazione EUR,Note,SIMBOLO QUOTA,VALUTA QUOTA\n"
    export.write_text(header + "02/01/2026,Directa,VWCE,,Acquisto,2,100,,,,,,VWCE,EUR\n")

    assert preview_movimenti(export).valid_rows == 1


def test_import_preserves_context_and_maps_operational_types(tmp_path: Path) -> None:
    export = tmp_path / "movimenti.csv"
    export.write_text(
        HEADER
        + "02/01/2026,Directa,EQQQ,IE0032077012,Saldo iniziale,2,100,,,,,Data e costo stimati,EQQQ.MI,GBP\n"
        + "03/01/2026,Directa,EQQQ,IE0032077012,Trasferimento in entrata,1,101,,,,,Da altro conto,EQQQ.MI,GBP\n"
        + '04/01/2026,Directa,EQQQ,IE0032077012,Rettifica,"-0,5",0,,,,,Correzione quantita,EQQQ.MI,GBP\n'
    )

    preview = preview_movimenti(export)

    assert preview.errors == []
    assert [row.kind for row in preview.rows] == ["OPENING_BALANCE", "TRANSFER_IN", "ADJUSTMENT"]
    assert preview.rows[0].note == "Data e costo stimati"
    assert preview.rows[0].original_currency == "GBP"
    assert preview.rows[2].quantity == Decimal("-0.5")
