from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Identified(Base):
    __abstract__ = True
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class User(Identified):
    __tablename__ = "users"
    username: Mapped[str] = mapped_column(String(100), unique=True)


class Account(Identified):
    __tablename__ = "accounts"
    name: Mapped[str] = mapped_column(String(200), unique=True)


class Instrument(Identified):
    __tablename__ = "instruments"
    ticker: Mapped[str] = mapped_column(String(64), unique=True)
    isin: Mapped[str | None] = mapped_column(String(32), nullable=True)


class Operation(Identified):
    __tablename__ = "operations"
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id"))
    kind: Mapped[str] = mapped_column(String(32))
    quantity: Mapped[Numeric] = mapped_column(Numeric(24, 10))
    unit_price_eur: Mapped[Numeric] = mapped_column(Numeric(24, 10), server_default="0")
    fee_eur: Mapped[Numeric | None] = mapped_column(Numeric(24, 10), nullable=True)
    dividend_eur: Mapped[Numeric | None] = mapped_column(Numeric(24, 10), nullable=True)
    trade_date: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    source_order: Mapped[int] = mapped_column(Integer, server_default="0")
    cancelled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")


class OperationRevision(Identified):
    __tablename__ = "operation_revisions"
    operation_id: Mapped[int] = mapped_column(ForeignKey("operations.id"))
    reason: Mapped[str] = mapped_column(Text())
    action: Mapped[str] = mapped_column(String(32), server_default="REVISE")
    supersedes_operation_id: Mapped[int | None] = mapped_column(ForeignKey("operations.id"), nullable=True)


class Observation(Identified):
    __tablename__ = "observations"
    __table_args__ = (UniqueConstraint("instrument_id", "provider", "observed_at", name="uq_observation_source_time"),)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id"))
    provider: Mapped[str] = mapped_column(String(100))
    price: Mapped[Numeric] = mapped_column(Numeric(24, 10))
    raw_price: Mapped[Numeric] = mapped_column(Numeric(24, 10), server_default="0")
    currency: Mapped[str] = mapped_column(String(8), server_default="EUR")
    fx_to_eur: Mapped[Numeric] = mapped_column(Numeric(24, 10), server_default="1")
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Benchmark(Identified):
    __tablename__ = "benchmarks"
    name: Mapped[str] = mapped_column(String(200), unique=True)


class ImportRun(Identified):
    __tablename__ = "import_runs"
    source_hash: Mapped[str] = mapped_column(String(128), unique=True)


class ImportRow(Identified):
    __tablename__ = "import_rows"
    import_run_id: Mapped[int] = mapped_column(ForeignKey("import_runs.id"))
    source_row: Mapped[int] = mapped_column(Integer)
