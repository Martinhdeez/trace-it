"""Use cases and versioned agent configuration.

A process now belongs to a use case, which holds the description (domain conventions) and
the agent configuration shared by its processes. Every existing process gets a use case of
its own, with its name and description.

Revision ID: 0002
Revises: 0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "use_cases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_use_cases")),
        sa.UniqueConstraint("name", name=op.f("uq_use_cases_name")),
    )
    op.create_table(
        "agent_configs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("use_case_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("author", sa.String(), nullable=False),
        sa.Column("note", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["use_case_id"], ["use_cases.id"], name=op.f("fk_agent_configs_use_case_id")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_agent_configs")),
        sa.UniqueConstraint(
            "use_case_id", "role", "version", name=op.f("uq_agent_configs_use_case_id_role_version")
        ),
    )
    op.create_index(
        op.f("ix_agent_configs_use_case_id"), "agent_configs", ["use_case_id"], unique=False
    )
    op.create_index(
        "uq_agent_configs_active",
        "agent_configs",
        ["use_case_id", "role"],
        unique=True,
        postgresql_where=sa.text("active"),
    )

    op.add_column("processes", sa.Column("use_case_id", sa.Integer(), nullable=True))
    op.execute("INSERT INTO use_cases (name, description) SELECT name, description FROM processes")
    op.execute("UPDATE processes p SET use_case_id = u.id FROM use_cases u WHERE u.name = p.name")
    op.alter_column("processes", "use_case_id", nullable=False)
    op.create_foreign_key(
        op.f("fk_processes_use_case_id"), "processes", "use_cases", ["use_case_id"], ["id"]
    )
    op.create_index(op.f("ix_processes_use_case_id"), "processes", ["use_case_id"])
    op.drop_column("processes", "description")


def downgrade() -> None:
    op.add_column(
        "processes",
        sa.Column("description", sa.String(), nullable=False, server_default=""),
    )
    op.execute(
        "UPDATE processes p SET description = u.description FROM use_cases u "
        "WHERE u.id = p.use_case_id"
    )
    op.drop_index(op.f("ix_processes_use_case_id"), table_name="processes")
    op.drop_constraint(op.f("fk_processes_use_case_id"), "processes", type_="foreignkey")
    op.drop_column("processes", "use_case_id")
    op.drop_index("uq_agent_configs_active", table_name="agent_configs")
    op.drop_index(op.f("ix_agent_configs_use_case_id"), table_name="agent_configs")
    op.drop_table("agent_configs")
    op.drop_table("use_cases")
