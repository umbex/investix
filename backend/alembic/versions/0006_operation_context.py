"""preserve complete operation context without rewriting imported rows

Revision ID: 0006_operation_context
Revises: 0005_benchmark_configuration
"""

from alembic import op
import sqlalchemy as sa


revision = "0006_operation_context"
down_revision = "0005_benchmark_configuration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("operations", sa.Column("original_unit_price", sa.Numeric(24, 10), nullable=True))
    op.add_column("operations", sa.Column("original_currency", sa.String(8), nullable=True))
    op.add_column("operations", sa.Column("settlement_date", sa.Date(), nullable=True))
    op.add_column("operations", sa.Column("note", sa.Text(), nullable=True))
    op.add_column("operations", sa.Column("is_approximate", sa.Boolean(), server_default=sa.text("false"), nullable=False))


def downgrade() -> None:
    op.drop_column("operations", "is_approximate")
    op.drop_column("operations", "note")
    op.drop_column("operations", "settlement_date")
    op.drop_column("operations", "original_currency")
    op.drop_column("operations", "original_unit_price")
