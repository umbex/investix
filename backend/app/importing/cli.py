"""Repeatable local command for a one-shot STOCKS-26 import."""

import argparse
import json
from decimal import Decimal
from pathlib import Path

from app.db import create_session_factory
from app.importing.finalize import FinalizationError, finalize_preview
from app.importing.stocks26 import preview_movimenti
from app.importing.reconcile import ReconciliationReport


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Preview or finalize a STOCKS-26 MOVIMENTI CSV import")
    parser.add_argument("source", type=Path, help="CSV export from the MOVIMENTI tab")
    parser.add_argument("--finalize", action="store_true", help="Persist the preview only if it has no errors")
    parser.add_argument("--reconciliation-report", type=Path, help="JSON report produced by reconcile_cli")
    args = parser.parse_args(argv)

    preview = preview_movimenti(args.source)
    print(f"Hash sorgente: {preview.source_hash}")
    print(f"Righe valide: {preview.valid_rows}")
    if preview.errors:
        print("Anomalie:")
        for error in preview.errors:
            print(f"- {error}")
        return 2
    if not args.finalize:
        print("Preview completata: nessun dato è stato scritto.")
        return 0
    if args.reconciliation_report is None:
        print("Importazione non eseguita: serve un report di riconciliazione (--reconciliation-report)")
        return 3
    payload = json.loads(args.reconciliation_report.read_text(encoding="utf-8"))
    reconciliation = ReconciliationReport(bool(payload["passed"]), Decimal(payload["quantity_tolerance"]), {})

    with create_session_factory()() as session:
        try:
            run_id = finalize_preview(session, preview, reconciliation=reconciliation)
        except FinalizationError as error:
            print(f"Importazione non eseguita: {error}")
            return 3
    print(f"Importazione completata. Import run: {run_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
