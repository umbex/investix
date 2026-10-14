from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator


OperationKind = Literal["BUY", "SELL", "OPENING_BALANCE", "DIVIDEND", "FEE", "SPLIT", "TRANSFER_IN", "TRANSFER_OUT", "ADJUSTMENT"]


class OperationCreate(BaseModel):
    account_name: str = Field(min_length=1, max_length=200)
    ticker: str = Field(min_length=1, max_length=64)
    kind: OperationKind
    quantity: Decimal
    unit_price_eur: Decimal = Field(ge=0)
    trade_date: date
    source_order: int = Field(ge=0)
    fee_eur: Decimal | None = Field(default=None, ge=0)
    dividend_eur: Decimal | None = Field(default=None, ge=0)
    original_unit_price: Decimal | None = Field(default=None, ge=0)
    original_currency: str | None = Field(default=None, min_length=3, max_length=8)
    settlement_date: date | None = None
    note: str | None = Field(default=None, max_length=4000)
    is_approximate: bool = False

    @model_validator(mode="after")
    def quantities_for_position_changes_are_positive(self) -> "OperationCreate":
        if self.kind in {"BUY", "SELL", "OPENING_BALANCE", "SPLIT", "TRANSFER_IN", "TRANSFER_OUT"} and self.quantity <= 0:
            raise ValueError("La quantità deve essere positiva")
        if self.kind == "ADJUSTMENT" and self.quantity == 0:
            raise ValueError("La rettifica deve modificare la quantità")
        return self


class OperationRevisionRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)
    quantity: Decimal | None = Field(default=None, gt=0)
    unit_price_eur: Decimal | None = Field(default=None, ge=0)
    trade_date: date | None = None
    source_order: int | None = Field(default=None, ge=0)
    fee_eur: Decimal | None = Field(default=None, ge=0)
    dividend_eur: Decimal | None = Field(default=None, ge=0)
    original_unit_price: Decimal | None = Field(default=None, ge=0)
    original_currency: str | None = Field(default=None, min_length=3, max_length=8)
    settlement_date: date | None = None
    note: str | None = Field(default=None, max_length=4000)
    is_approximate: bool | None = None


class CancelRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)


class OperationResponse(BaseModel):
    id: int
    account_name: str
    ticker: str
    kind: OperationKind
    quantity: Decimal
    unit_price_eur: Decimal
    trade_date: date
    source_order: int
    fee_eur: Decimal | None
    dividend_eur: Decimal | None
    original_unit_price: Decimal | None
    original_currency: str | None
    settlement_date: date | None
    note: str | None
    is_approximate: bool


class OperationPage(BaseModel):
    items: list[OperationResponse]
    total: int
