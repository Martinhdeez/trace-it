"""Optional extraction hints on process symbols."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("symbols", sa.Column("extraction", JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("symbols", "extraction")
