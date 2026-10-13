from datetime import date
from decimal import Decimal

from app.importing.stocks26_price_history import normalize_snapshot_rows


def test_normalizes_usd_and_gbx_prices_using_same_or_prior_fx_date() -> None:
    rows = [
        _row(aapl_date=excel_day(date(2026, 1, 5)), aapl_price=Decimal("100"), eqqq_date=excel_day(date(2026, 1, 5)), eqqq_price=Decimal("250")),
        _row(usd_fx_date=excel_day(date(2026, 1, 2)), usd_fx=Decimal("0.8"), gbp_fx_date=excel_day(date(2026, 1, 2)), gbp_fx=Decimal("1.2")),
    ]

    result = normalize_snapshot_rows(rows)

    assert [(item.ticker, item.currency, item.price, item.fx_to_eur) for item in result.observations] == [
        ("AAPL", "USD", Decimal("100"), Decimal("0.8")),
        ("EQQQ", "GBX", Decimal("250"), Decimal("1.2")),
    ]


def test_ignores_empty_price_cells_and_rejects_missing_fx() -> None:
    rows = [_row(aapl_date=excel_day(date(2026, 1, 5)), aapl_price=Decimal("100"))]

    result = normalize_snapshot_rows(rows)

    assert result.errors == ["AAPL 2026-01-05: cambio USD/EUR non disponibile"]
    assert result.observations == []


def test_normalizes_the_qqq_price_return_benchmark_with_historical_usd_fx() -> None:
    rows = [
        _row(
            qqq_date=excel_day(date(2026, 1, 5)),
            qqq_price=Decimal("500"),
            usd_fx_date=excel_day(date(2026, 1, 2)),
            usd_fx=Decimal("0.8"),
        )
    ]

    result = normalize_snapshot_rows(rows)

    assert result.errors == []
    assert [(item.ticker, item.currency, item.price, item.fx_to_eur) for item in result.observations] == [
        ("QQQ", "USD", Decimal("500"), Decimal("0.8")),
    ]


def excel_day(value: date) -> float:
    return float((value - date(1899, 12, 30)).days)


def _row(
    *,
    aapl_date: float | None = None,
    aapl_price: Decimal | None = None,
    eqqq_date: float | None = None,
    eqqq_price: Decimal | None = None,
    qqq_date: float | None = None,
    qqq_price: Decimal | None = None,
    gbp_fx_date: float | None = None,
    gbp_fx: Decimal | None = None,
    usd_fx_date: float | None = None,
    usd_fx: Decimal | None = None,
) -> list[object | None]:
    row: list[object | None] = [None] * 84
    row[0], row[1] = aapl_date, aapl_price
    row[4], row[5] = eqqq_date, eqqq_price
    row[12], row[13] = qqq_date, qqq_price
    row[80], row[81] = gbp_fx_date, gbp_fx
    row[82], row[83] = usd_fx_date, usd_fx
    return row
