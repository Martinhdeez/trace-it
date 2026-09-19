"""A dedicated API manager and transactional audit log for database administration."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "database_api_changes",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("table_name", sa.String(), nullable=False),
        sa.Column("operation", sa.String(), nullable=False),
        sa.Column("key", JSONB(), nullable=False),
        sa.Column("before", JSONB()),
        sa.Column("after", JSONB()),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("actor", sa.String(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.execute(
        "INSERT INTO users (name, email, role) "
        "VALUES ('Trace-it API', 'trace-it-api@localhost', 'manager') "
        "ON CONFLICT (email) DO NOTHING"
    )


def downgrade() -> None:
    op.drop_table("database_api_changes")
    # Keep the manager: application history may reference its id.
