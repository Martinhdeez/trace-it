"""Published process configurations, one draft, and captured execution inputs."""

import hashlib
import json

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("fk_rules_process_id_decision", "rules", type_="foreignkey")
    op.create_table(
        "process_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("process_id", sa.Integer(), sa.ForeignKey("processes.id"), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("process_versions.id")),
        sa.Column("snapshot", JSONB(), nullable=False),
        sa.Column("content_hash", sa.String(), nullable=False),
        sa.Column("validation", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("author", sa.String(), nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("process_id", "number"),
    )
    op.create_index("ix_process_versions_process_id", "process_versions", ["process_id"])
    op.add_column("processes", sa.Column("active_version_id", sa.Integer()))
    op.create_foreign_key(
        "fk_processes_active_version_id",
        "processes",
        "process_versions",
        ["active_version_id"],
        ["id"],
    )
    op.create_table(
        "process_drafts",
        sa.Column("process_id", sa.Integer(), sa.ForeignKey("processes.id"), primary_key=True),
        sa.Column("base_version_id", sa.Integer(), sa.ForeignKey("process_versions.id")),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("snapshot", JSONB(), nullable=False),
        sa.Column("author", sa.String(), nullable=False),
        sa.Column("validation", JSONB()),
    )
    op.create_table(
        "executions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("process_id", sa.Integer(), sa.ForeignKey("processes.id"), nullable=False),
        sa.Column("version_id", sa.Integer(), sa.ForeignKey("process_versions.id"), nullable=False),
        sa.Column("inputs", JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_executions_process_id", "executions", ["process_id"])
    op.add_column(
        "decisions", sa.Column("version_id", sa.Integer(), sa.ForeignKey("process_versions.id"))
    )
    op.add_column(
        "decisions", sa.Column("execution_id", sa.Integer(), sa.ForeignKey("executions.id"))
    )
    # Baseline today's configuration, never attribute it to historical decisions.
    bind = op.get_bind()

    def rows(query, **params):
        return [dict(r) for r in bind.execute(sa.text(query), params).mappings()]

    for process in rows(
        "SELECT p.id, p.name, p.use_case_id, p.decision_review, u.description FROM "
        "processes p JOIN use_cases u ON u.id=p.use_case_id"
    ):
        pid = process["id"]
        process["decision_types"] = rows(
            "SELECT name, priority, is_default, requires_human FROM decision_types "
            "WHERE process_id=:pid ORDER BY name",
            pid=pid,
        )
        process["symbols"] = rows(
            "SELECT name, type, description, required FROM symbols WHERE "
            "process_id=:pid ORDER BY name",
            pid=pid,
        )
        rules = rows(
            "SELECT id, norm_rule_id, text, type, decision, code, tests, hash, "
            "report, status FROM rules WHERE process_id=:pid AND status IN "
            "('active','blocked') ORDER BY id",
            pid=pid,
        )
        agents = {
            r["role"]: {"config_id": r["id"], "settings": r["config"]}
            for r in rows(
                "SELECT id, role, config FROM agent_configs WHERE use_case_id=:uid AND active",
                uid=process["use_case_id"],
            )
        }
        from app.core.config import settings
        from app.features.agents.llm import prompt
        from app.features.use_cases.schemas import ROLES, AgentSettings

        for role in ROLES:
            agent = agents.setdefault(
                role, {"config_id": None, "settings": AgentSettings().model_dump(mode="json")}
            )
            agent["settings"]["model"] = agent["settings"].get("model") or getattr(
                settings, f"{role}_model"
            )
        guidance = {
            f"norm:{r['id']}": r["text"]
            for r in rows(
                "SELECT a.id, p.text FROM norm_adoptions a JOIN norm_proposals p ON "
                "p.id=a.proposal_id JOIN learning_analyses l ON l.id=p.analysis_id "
                "WHERE l.process_id=:pid AND a.approved AND p.kind='guidance' ORDER "
                "BY a.id",
                pid=pid,
            )
        }
        snapshot = {
            "process": process,
            "rules": rules,
            "agents": agents,
            "guidance": guidance,
            "reviewer_prompt": prompt("decision_reviewer"),
        }
        encoded = json.dumps(snapshot, sort_keys=True)
        key = bind.execute(
            sa.text(
                "INSERT INTO process_versions(process_id, number, snapshot, "
                "content_hash, author, reason) VALUES (:pid, 1, CAST(:snapshot AS "
                "jsonb), :hash, 'migration', 'Baseline at migration; prior decisions "
                "remain legacy') RETURNING id"
            ),
            {"pid": pid, "snapshot": encoded, "hash": hashlib.sha256(encoded.encode()).hexdigest()},
        ).scalar_one()
        bind.execute(
            sa.text("UPDATE processes SET active_version_id=:key WHERE id=:pid"),
            {"key": key, "pid": pid},
        )


def downgrade():
    op.create_foreign_key(
        "fk_rules_process_id_decision",
        "rules",
        "decision_types",
        ["process_id", "decision"],
        ["process_id", "name"],
    )
    op.drop_column("decisions", "execution_id")
    op.drop_column("decisions", "version_id")
    op.drop_table("executions")
    op.drop_table("process_drafts")
    op.drop_constraint("fk_processes_active_version_id", "processes", type_="foreignkey")
    op.drop_column("processes", "active_version_id")
    op.drop_table("process_versions")
