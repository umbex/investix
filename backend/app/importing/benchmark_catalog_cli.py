"""Configure an initial benchmark without making Google Sheets a runtime dependency."""

import argparse

from app.db import create_session_factory
from app.schemas.benchmarks import BenchmarkConfig
from app.services.benchmarks import configure_benchmark


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Configure an Investix benchmark")
    parser.add_argument("--name", required=True)
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--venue", required=True)
    parser.add_argument("--currency", required=True)
    parser.add_argument("--methodology", choices=["price_return", "total_return"], default="price_return")
    parser.add_argument("--note")
    args = parser.parse_args(argv)
    payload = BenchmarkConfig(
        name=args.name,
        ticker=args.ticker,
        quote_symbol=args.symbol,
        quote_venue=args.venue,
        quote_currency=args.currency,
        methodology=args.methodology,
        note=args.note,
    )
    with create_session_factory()() as session:
        benchmark = configure_benchmark(session, payload)
    print(f"Benchmark configurato: {benchmark.name} ({benchmark.ticker})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
