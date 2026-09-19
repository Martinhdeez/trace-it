"""A plain one-line summary on each rule, for the console's lists."""

import sqlalchemy as sa

from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("rules", sa.Column("summary", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("rules", "summary")
