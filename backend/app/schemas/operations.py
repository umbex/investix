from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator


OperationKind = Literal["BUY", "SELL", "DIVIDEND", "FEE", "SPLIT"]


class OperationCreate(BaseModel):
    account_name: str = Field(min_length=1, max_length=200)
    ticker: str = Field(min_length=1, max_length=64)
    kind: OperationKind
    quantity: Decimal = Field(ge=0)
    unit_price_eur: Decimal = Field(ge=0)
    trade_date: date
    source_order: int = Field(ge=0)
    fee_eur: Decimal | None = Field(default=None, ge=0)
    dividend_eur: Decimal | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def quantities_for_position_changes_are_positive(self) -> "OperationCreate":
        if self.kind in {"BUY", "SELL", "SPLIT"} and self.quantity <= 0:
            raise ValueError("La quantità deve essere positiva")
        return self


class OperationRevisionRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)
    quantity: Decimal | None = Field(default=None, gt=0)
    unit_price_eur: Decimal | None = Field(default=None, ge=0)
    trade_date: date | None = None
    source_order: int | None = Field(default=None, ge=0)
    fee_eur: Decimal | None = Field(default=None, ge=0)
    dividend_eur: Decimal | None = Field(default=None, ge=0)


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


class OperationPage(BaseModel):
    items: list[OperationResponse]
    total: int
