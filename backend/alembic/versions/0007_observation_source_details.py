"""store quote source details and data status

Revision ID: 0007_observation_source_details
Revises: 0006_operation_context
"""

from alembic import op
import sqlalchemy as sa

revision = "0007_observation_source_details"
down_revision = "0006_operation_context"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("observations", sa.Column("source_symbol", sa.String(64), nullable=True))
    op.add_column("observations", sa.Column("venue", sa.String(128), nullable=True))
    op.add_column("observations", sa.Column("quote_unit", sa.String(16), nullable=True))
    op.add_column("observations", sa.Column("price_field", sa.String(32), nullable=True))
    op.add_column("observations", sa.Column("status", sa.String(32), server_default="valid", nullable=False))
    op.add_column("observations", sa.Column("fx_provider", sa.String(100), nullable=True))


def downgrade() -> None:
    for name in ("fx_provider", "status", "price_field", "quote_unit", "venue", "source_symbol"):
        op.drop_column("observations", name)
