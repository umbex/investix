"""Create a frozen normalized CSV from a read-only STOCKS-26 XLSX export."""

import argparse
from pathlib import Path

from app.importing.stocks26_price_history import extract_xlsx, write_normalized_csv


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Normalize a STOCKS-26 _PRICE_HISTORY XLSX snapshot")
    parser.add_argument("source", type=Path, help="Read-only exported STOCKS-26 XLSX")
    parser.add_argument("destination", type=Path, help="Normalized CSV destination")
    args = parser.parse_args(argv)
    snapshot = extract_xlsx(args.source)
    write_normalized_csv(snapshot, args.destination)
    print(f"Osservazioni normalizzate: {len(snapshot.observations)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
