"""store explicit benchmark metadata and methodology

Revision ID: 0005_benchmark_configuration
Revises: 0004_instrument_quote_metadata
"""

from alembic import op
import sqlalchemy as sa


revision = "0005_benchmark_configuration"
down_revision = "0004_instrument_quote_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("benchmarks", sa.Column("ticker", sa.String(64), nullable=True))
    op.add_column("benchmarks", sa.Column("quote_symbol", sa.String(64), nullable=True))
    op.add_column("benchmarks", sa.Column("quote_venue", sa.String(128), nullable=True))
    op.add_column("benchmarks", sa.Column("quote_currency", sa.String(8), server_default="EUR", nullable=False))
    op.add_column("benchmarks", sa.Column("methodology", sa.String(32), server_default="price_return", nullable=False))
    op.add_column("benchmarks", sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False))
    op.add_column("benchmarks", sa.Column("note", sa.Text(), nullable=True))
    op.create_unique_constraint("uq_benchmark_ticker", "benchmarks", ["ticker"])


def downgrade() -> None:
    op.drop_constraint("uq_benchmark_ticker", "benchmarks", type_="unique")
    op.drop_column("benchmarks", "note")
    op.drop_column("benchmarks", "active")
    op.drop_column("benchmarks", "methodology")
    op.drop_column("benchmarks", "quote_currency")
    op.drop_column("benchmarks", "quote_venue")
    op.drop_column("benchmarks", "quote_symbol")
    op.drop_column("benchmarks", "ticker")
