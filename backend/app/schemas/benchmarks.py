from typing import Literal

from pydantic import BaseModel, Field


BenchmarkMethodology = Literal["price_return", "total_return"]


class BenchmarkConfig(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    ticker: str = Field(min_length=1, max_length=64)
    quote_symbol: str = Field(min_length=1, max_length=64)
    quote_venue: str = Field(min_length=1, max_length=128)
    quote_currency: str = Field(min_length=3, max_length=8)
    methodology: BenchmarkMethodology = "price_return"
    active: bool = True
    note: str | None = Field(default=None, max_length=2000)
