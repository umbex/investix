"""Verify an exported STOCKS-26 movement file against the local ledger."""

import argparse
import json
from pathlib import Path

from app.db import create_session_factory
from app.importing.ledger_reconciliation import reconcile_preview_with_ledger
from app.importing.stocks26 import preview_movimenti


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reconcile STOCKS-26 MOVIMENTI against Investix")
    parser.add_argument("source", type=Path, help="Read-only MOVIMENTI CSV export")
    parser.add_argument("--report", type=Path, help="Write the reconciliation report as JSON")
    args = parser.parse_args(argv)
    preview = preview_movimenti(args.source)
    with create_session_factory()() as session:
        report = reconcile_preview_with_ledger(session, preview)
    if args.report:
        args.report.write_text(json.dumps(report.as_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Riconciliazione quantità: {report.quantity_status}")
    print(f"Coppie ticker/conto verificate: {len(report.reference_quantities)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
