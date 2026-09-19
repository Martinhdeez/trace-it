"""Mail reception activity, reader stages and worker heartbeat."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = depends_on = None


def upgrade():
    op.add_column("mail_accounts", sa.Column("heartbeat_at", sa.DateTime(timezone=True)))
    op.add_column("mail_accounts", sa.Column("worker_phase", sa.String()))
    op.add_column("mail_attachments", sa.Column("reading_at", sa.DateTime(timezone=True)))
    op.add_column("mail_attachments", sa.Column("completed_at", sa.DateTime(timezone=True)))
    op.create_table(
        "mail_activity",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("process_id", sa.Integer(), sa.ForeignKey("processes.id"), nullable=False),
        sa.Column("message_id", sa.Integer(), sa.ForeignKey("mail_messages.id"), nullable=False),
        sa.Column("attachment_id", sa.Integer(), sa.ForeignKey("mail_attachments.id")),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("data", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_mail_activity_process_id", "mail_activity", ["process_id"])
    op.create_index("ix_mail_activity_message_id", "mail_activity", ["message_id"])
    op.create_table(
        "mail_activity_reads",
        sa.Column("process_id", sa.Integer(), sa.ForeignKey("processes.id"), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("through_id", sa.BigInteger(), nullable=False, server_default="0"),
    )


def downgrade():
    op.drop_table("mail_activity_reads")
    op.drop_table("mail_activity")
    op.drop_column("mail_attachments", "completed_at")
    op.drop_column("mail_attachments", "reading_at")
    op.drop_column("mail_accounts", "worker_phase")
    op.drop_column("mail_accounts", "heartbeat_at")
