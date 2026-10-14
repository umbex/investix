"""mark instruments that should be monitored without a portfolio position

Revision ID: 0008_instrument_watch
Revises: 0007_observation_source_details
"""

from alembic import op
import sqlalchemy as sa


revision = "0008_instrument_watch"
down_revision = "0007_observation_source_details"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("instruments", sa.Column("is_watch", sa.Boolean(), server_default=sa.text("false"), nullable=False))


def downgrade() -> None:
    op.drop_column("instruments", "is_watch")
