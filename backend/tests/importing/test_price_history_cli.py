from pathlib import Path

import pytest

from app.importing import price_history_cli


def test_price_history_cli_requires_a_source_file() -> None:
    with pytest.raises(SystemExit, match="0"):
        price_history_cli.main(["--help"])
