"""Persistent discovery drafts and append-only revisions.

Revision ID: 0011
Revises: 0010
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "process_drafts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("process_id", sa.Integer(), sa.ForeignKey("processes.id")),
        sa.Column("use_case_id", sa.Integer(), sa.ForeignKey("use_cases.id")),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("published_process_id", sa.Integer(), sa.ForeignKey("processes.id")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_table(
        "draft_revisions",
        sa.Column("draft_id", sa.Integer(), sa.ForeignKey("process_drafts.id"), primary_key=True),
        sa.Column("number", sa.Integer(), primary_key=True),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("data", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade():
    op.drop_table("draft_revisions")
    op.drop_table("process_drafts")
