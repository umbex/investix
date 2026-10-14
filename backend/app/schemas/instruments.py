from pydantic import BaseModel, Field


class WatchInstrumentConfig(BaseModel):
    quote_symbol: str = Field(min_length=1, max_length=64)
    quote_venue: str = Field(min_length=1, max_length=128)
    quote_currency: str = Field(min_length=3, max_length=8)
    watch: bool = True
