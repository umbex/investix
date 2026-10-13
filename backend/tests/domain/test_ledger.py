from datetime import date
from decimal import Decimal

from app.domain.ledger import LedgerOperation, rebuild_position


def operation(
    kind: str,
    *,
    quantity: str = "0",
    price: str = "0",
    order: int = 1,
    fee: str | None = None,
    dividend: str | None = None,
    split_ratio: str | None = None,
) -> LedgerOperation:
    return LedgerOperation(
        id=order,
        trade_date=date(2026, 1, 2),
        source_order=order,
        kind=kind,
        quantity=Decimal(quantity),
        unit_price_eur=Decimal(price),
        fee_eur=Decimal(fee) if fee is not None else None,
        dividend_eur=Decimal(dividend) if dividend is not None else None,
        split_ratio=Decimal(split_ratio) if split_ratio is not None else None,
    )


def test_average_cost_partial_sale_and_repurchase_keep_realised_pnl() -> None:
    snapshot = rebuild_position(
        [
            operation("BUY", quantity="10", price="100", fee="10", order=1),
            operation("SELL", quantity="4", price="120", fee="4", order=2),
            operation("BUY", quantity="2", price="90", order=3),
        ]
    )

    assert snapshot.quantity == Decimal("8")
    assert snapshot.open_cost_eur == Decimal("786")
    assert snapshot.average_cost_eur == Decimal("98.25")
    assert snapshot.realized.pnl_eur == Decimal("72")
    assert snapshot.fees.recorded_eur == Decimal("14")
    assert snapshot.fees.is_complete is False


def test_total_sale_keeps_realised_pnl_after_zero_position() -> None:
    snapshot = rebuild_position(
        [operation("BUY", quantity="2", price="100"), operation("SELL", quantity="2", price="125", order=2)]
    )

    assert snapshot.quantity == 0
    assert snapshot.open_cost_eur == 0
    assert snapshot.realized.pnl_eur == Decimal("50")


def test_optional_dividends_and_fees_are_not_silently_zeroed() -> None:
    snapshot = rebuild_position(
        [operation("BUY", quantity="1", price="100"), operation("DIVIDEND", dividend="3", order=2), operation("DIVIDEND", order=3)]
    )

    assert snapshot.dividends.recorded_eur == Decimal("3")
    assert snapshot.dividends.is_complete is False
    assert snapshot.fees.recorded_eur is None
    assert snapshot.fees.is_complete is False


def test_split_preserves_open_cost_and_changes_average_cost() -> None:
    snapshot = rebuild_position(
        [operation("BUY", quantity="2", price="100"), operation("SPLIT", split_ratio="3", order=2)]
    )

    assert snapshot.quantity == Decimal("6")
    assert snapshot.open_cost_eur == Decimal("200")
    assert snapshot.average_cost_eur == Decimal("33.33333333333333333333333333")


def test_opening_balance_transfer_and_negative_adjustment_preserve_cost_without_realised_pnl() -> None:
    snapshot = rebuild_position(
        [
            operation("OPENING_BALANCE", quantity="10", price="100", order=1),
            operation("TRANSFER_OUT", quantity="2", price="100", order=2),
            operation("TRANSFER_IN", quantity="1", price="100", order=3),
            operation("ADJUSTMENT", quantity="-1", order=4),
        ]
    )

    assert snapshot.quantity == Decimal("8")
    assert snapshot.open_cost_eur == Decimal("800")
    assert snapshot.realized.pnl_eur == Decimal("0")
