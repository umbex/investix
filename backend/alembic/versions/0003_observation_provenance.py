"""store market observation provenance and idempotency key

Revision ID: 0003_observation_provenance
Revises: 0002_operation_details
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_observation_provenance"
down_revision = "0002_operation_details"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("observations", sa.Column("raw_price", sa.Numeric(24, 10), server_default="0", nullable=False))
    op.add_column("observations", sa.Column("currency", sa.String(8), server_default="EUR", nullable=False))
    op.add_column("observations", sa.Column("fx_to_eur", sa.Numeric(24, 10), server_default="1", nullable=False))
    op.add_column("observations", sa.Column("observed_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False))
    op.create_unique_constraint("uq_observation_source_time", "observations", ["instrument_id", "provider", "observed_at"])


def downgrade() -> None:
    op.drop_constraint("uq_observation_source_time", "observations", type_="unique")
    op.drop_column("observations", "observed_at")
    op.drop_column("observations", "fx_to_eur")
    op.drop_column("observations", "currency")
    op.drop_column("observations", "raw_price")
