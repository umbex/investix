from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal


OperationKind = Literal["BUY", "SELL", "DIVIDEND", "FEE", "SPLIT"]


@dataclass(frozen=True)
class LedgerOperation:
    id: int
    trade_date: date
    source_order: int
    kind: OperationKind
    quantity: Decimal = Decimal("0")
    unit_price_eur: Decimal = Decimal("0")
    fee_eur: Decimal | None = None
    dividend_eur: Decimal | None = None
    split_ratio: Decimal | None = None


@dataclass(frozen=True)
class OptionalAmount:
    recorded_eur: Decimal | None
    is_complete: bool


@dataclass(frozen=True)
class RealizedPnl:
    pnl_eur: Decimal


@dataclass(frozen=True)
class PositionSnapshot:
    quantity: Decimal
    open_cost_eur: Decimal
    average_cost_eur: Decimal
    realized: RealizedPnl
    fees: OptionalAmount
    dividends: OptionalAmount


def rebuild_position(operations: list[LedgerOperation]) -> PositionSnapshot:
    """Reconstruct a single account/instrument position with average-cost accounting."""
    quantity = Decimal("0")
    open_cost = Decimal("0")
    realized = Decimal("0")
    fees: list[Decimal | None] = []
    dividends: list[Decimal | None] = []

    for operation in sorted(operations, key=lambda item: (item.trade_date, item.source_order, item.id)):
        if operation.kind == "BUY":
            quantity += operation.quantity
            open_cost += operation.quantity * operation.unit_price_eur
            fees.append(operation.fee_eur)
            if operation.fee_eur is not None:
                open_cost += operation.fee_eur
        elif operation.kind == "SELL":
            if operation.quantity > quantity:
                raise ValueError("A sale cannot exceed the reconstructed open quantity")
            average_cost = open_cost / quantity if quantity else Decimal("0")
            cost_sold = average_cost * operation.quantity
            proceeds = operation.quantity * operation.unit_price_eur
            fees.append(operation.fee_eur)
            if operation.fee_eur is not None:
                proceeds -= operation.fee_eur
            realized += proceeds - cost_sold
            quantity -= operation.quantity
            open_cost -= cost_sold
        elif operation.kind == "DIVIDEND":
            dividends.append(operation.dividend_eur)
        elif operation.kind == "FEE":
            fees.append(operation.fee_eur)
        elif operation.kind == "SPLIT":
            if operation.split_ratio is None or operation.split_ratio <= 0:
                raise ValueError("A split requires a positive ratio")
            quantity *= operation.split_ratio

    if quantity == 0:
        open_cost = Decimal("0")
    return PositionSnapshot(
        quantity=quantity,
        open_cost_eur=open_cost,
        average_cost_eur=open_cost / quantity if quantity else Decimal("0"),
        realized=RealizedPnl(pnl_eur=realized),
        fees=_optional_amount(fees),
        dividends=_optional_amount(dividends),
    )


def _optional_amount(values: list[Decimal | None]) -> OptionalAmount:
    recorded = [value for value in values if value is not None]
    return OptionalAmount(
        recorded_eur=sum(recorded, Decimal("0")) if recorded else None,
        is_complete=bool(values) and all(value is not None for value in values),
    )
