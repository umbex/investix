"""Persist a frozen normalized historical-price CSV without a Sheets runtime link."""

import argparse
from pathlib import Path

from app.db import create_session_factory
from app.providers.manual_csv import ManualCsvAdapter
from app.services.market_data import persist_observation


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import a normalized historical price CSV")
    parser.add_argument("source", type=Path, help="CSV with ticker,date,price,currency,fx_to_eur")
    args = parser.parse_args(argv)
    observations = ManualCsvAdapter(args.source).iter_observations()
    with create_session_factory()() as session:
        for observation in observations:
            persist_observation(session, observation)
    print(f"Osservazioni elaborate: {len(observations)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
