from datetime import date
from decimal import Decimal

from app.domain.portfolio_series import HistoricalOperation, HistoricalQuote, build_portfolio_series


def test_portfolio_series_uses_ledger_holdings_and_excludes_purchase_flow_from_twr() -> None:
    result = build_portfolio_series(
        operations=[HistoricalOperation(date(2026, 1, 2), "BUY", "VWCE", Decimal("1"), Decimal("100"))],
        quotes=[
            HistoricalQuote(date(2026, 1, 2), "VWCE", Decimal("100")),
            HistoricalQuote(date(2026, 1, 3), "VWCE", Decimal("110")),
        ],
    )

    assert [(point.day, point.value_eur, point.external_flow_eur) for point in result.points] == [
        (date(2026, 1, 2), Decimal("100"), Decimal("100")),
        (date(2026, 1, 3), Decimal("110"), Decimal("0")),
    ]
    assert result.total_return == Decimal("0.1")
    assert [point.cumulative_return for point in result.points] == [Decimal("0"), Decimal("0.1")]


def test_portfolio_series_skips_days_without_a_price_for_an_open_position() -> None:
    result = build_portfolio_series(
        operations=[HistoricalOperation(date(2026, 1, 2), "BUY", "VWCE", Decimal("1"), Decimal("100"))],
        quotes=[HistoricalQuote(date(2026, 1, 3), "VWCE", Decimal("110"))],
    )

    assert [point.day for point in result.points] == [date(2026, 1, 3)]
    assert result.total_return is None
