"""store explicit preferred quote metadata for an instrument

Revision ID: 0004_instrument_quote_metadata
Revises: 0003_observation_provenance
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_instrument_quote_metadata"
down_revision = "0003_observation_provenance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("instruments", sa.Column("quote_symbol", sa.String(64), nullable=True))
    op.add_column("instruments", sa.Column("quote_venue", sa.String(128), nullable=True))
    op.add_column("instruments", sa.Column("quote_currency", sa.String(8), nullable=True))


def downgrade() -> None:
    op.drop_column("instruments", "quote_currency")
    op.drop_column("instruments", "quote_venue")
    op.drop_column("instruments", "quote_symbol")
