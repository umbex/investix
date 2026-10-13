from pathlib import Path

from app.importing.stocks26 import preview_movimenti


HEADER = "DATA,CONTO,TICKER,ISIN,TIPO,QUANTITÀ,PREZZO EUR,COMMISSIONI EUR,IMPORTO MOVIMENTO EUR,CONTROVALORE EUR,FLUSSO OPERAZIONE EUR,NOTE,SIMBOLO QUOTA,VALUTA QUOTA\n"


def test_import_uses_actual_m_n_quote_headers_and_is_idempotent(tmp_path: Path) -> None:
    export = tmp_path / "movimenti.csv"
    export.write_text(HEADER + "2026-01-02,Directa,VWCE,,Acquisto,2,100,,,,,,VWCE,EUR\n")

    preview = preview_movimenti(export)

    assert preview.valid_rows == 1
    assert preview.rows[0].quote_symbol == "VWCE"
    assert preview.rows[0].quote_currency == "EUR"
    assert preview.source_hash == preview_movimenti(export).source_hash


def test_import_blocks_unknown_type_and_formula_error(tmp_path: Path) -> None:
    export = tmp_path / "movimenti.csv"
    export.write_text(HEADER + "2026-01-02,Directa,VWCE,,Mistero,2,#N/D,,,,,,,EUR\n")

    preview = preview_movimenti(export)

    assert preview.valid_rows == 0
    assert len(preview.errors) == 1
