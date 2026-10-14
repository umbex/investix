from pathlib import Path

import pytest

from app.importing import benchmark_catalog_cli, price_history_cli


def test_price_history_cli_requires_a_source_file() -> None:
    with pytest.raises(SystemExit, match="0"):
        price_history_cli.main(["--help"])


def test_benchmark_catalog_cli_exposes_repeatable_configuration() -> None:
    with pytest.raises(SystemExit, match="0"):
        benchmark_catalog_cli.main(["--help"])
