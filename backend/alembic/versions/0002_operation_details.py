"""add operation fields required by the auditable ledger

Revision ID: 0002_operation_details
Revises: 0001_core_schema
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_operation_details"
down_revision = "0001_core_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("operations", sa.Column("unit_price_eur", sa.Numeric(24, 10), server_default="0", nullable=False))
    op.add_column("operations", sa.Column("fee_eur", sa.Numeric(24, 10), nullable=True))
    op.add_column("operations", sa.Column("dividend_eur", sa.Numeric(24, 10), nullable=True))
    op.add_column("operations", sa.Column("trade_date", sa.Date(), server_default=sa.text("CURRENT_DATE"), nullable=False))
    op.add_column("operations", sa.Column("source_order", sa.Integer(), server_default="0", nullable=False))
    op.add_column("operations", sa.Column("cancelled", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("operation_revisions", sa.Column("action", sa.String(32), server_default="REVISE", nullable=False))
    op.add_column("operation_revisions", sa.Column("supersedes_operation_id", sa.Integer(), nullable=True))
    op.create_foreign_key("operation_revisions_supersedes_operation_id_fkey", "operation_revisions", "operations", ["supersedes_operation_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("operation_revisions_supersedes_operation_id_fkey", "operation_revisions", type_="foreignkey")
    op.drop_column("operation_revisions", "supersedes_operation_id")
    op.drop_column("operation_revisions", "action")
    op.drop_column("operations", "cancelled")
    op.drop_column("operations", "source_order")
    op.drop_column("operations", "trade_date")
    op.drop_column("operations", "dividend_eur")
    op.drop_column("operations", "fee_eur")
    op.drop_column("operations", "unit_price_eur")
