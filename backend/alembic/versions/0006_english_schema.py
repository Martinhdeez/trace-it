"""english schema

Renames every table, column, constraint and index to English (see docs/CONVENTIONS.md) and
rewrites the enum-like values and the JSON keys the system itself writes. Domain data is left
as it is: process names, symbol names, source rows, rule texts and decision names such as
PAGAR. Compiled rule code is not rewritten either: code compiled before this revision still
defines `evaluar` and returns `salta`/`motivo`, so recompile it (or reset the database).

Revision ID: 0006
Revises: 0005
"""

import json
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = {
    "config_llm": "llm_config",
    "ficheros": "files",
    "procesos": "processes",
    "usuarios": "users",
    "fuentes": "sources",
    "instancias": "instances",
    "simbolos": "symbols",
    "tipos_decision": "decision_types",
    "decisiones": "decisions",
    "eventos": "events",
    "extracciones": "extractions",
    "reglas": "rules",
    "hallazgos": "findings",
}

# By new table name.
COLUMNS = {
    "llm_config": {"papel": "role", "modelo": "model"},
    "files": {"nombre": "name", "contenido": "content", "texto": "text", "ingerido": "ingested_at"},
    "processes": {"nombre": "name", "descripcion": "description", "creado": "created_at"},
    "users": {"nombre": "name", "rol": "role", "creado": "created_at"},
    "sources": {
        "proceso_id": "process_id",
        "nombre": "name",
        "origen": "origin",
        "filas": "rows",
        "cargada": "loaded_at",
    },
    "instances": {
        "proceso_id": "process_id",
        "fichero_hash": "file_hash",
        "nombre": "name",
        "estado": "status",
        "motivo_revision": "review_reason",
        "simbolos": "symbols",
    },
    "symbols": {
        "proceso_id": "process_id",
        "nombre": "name",
        "tipo": "type",
        "descripcion": "description",
    },
    "decision_types": {
        "proceso_id": "process_id",
        "nombre": "name",
        "prioridad": "priority",
        "por_defecto": "is_default",
        "requiere_persona": "requires_human",
    },
    "decisions": {
        "instancia_id": "instance_id",
        "resultados": "results",
        "reglas_hash": "rules_hash",
        "autor": "author",
        "tipo_humana": "human_kind",
        "motivo": "reason",
        "creada": "created_at",
    },
    "events": {
        "instancia_id": "instance_id",
        "paso": "step",
        "datos": "data",
        "latencia_ms": "latency_ms",
        "coste": "cost",
        "creado": "created_at",
    },
    "extractions": {
        "instancia_id": "instance_id",
        "papel": "role",
        "modelo": "model",
        "simbolos": "symbols",
        "coste": "cost",
        "latencia_ms": "latency_ms",
        "creada": "created_at",
    },
    "rules": {
        "proceso_id": "process_id",
        "texto": "text",
        "tipo": "type",
        "codigo_a": "code_a",
        "codigo_b": "code_b",
        "estado": "status",
        "informe": "report",
        "creada": "created_at",
        "activada": "activated_at",
    },
    "findings": {
        "regla_id": "rule_id",
        "tipo": "type",
        "detalle": "detail",
        "creado": "created_at",
    },
}

# (new table, old name, new name). Unique and primary key constraints rename their index too.
CONSTRAINTS = [
    ("llm_config", "pk_config_llm", "pk_llm_config"),
    ("files", "pk_ficheros", "pk_files"),
    ("processes", "pk_procesos", "pk_processes"),
    ("processes", "uq_procesos_nombre", "uq_processes_name"),
    ("users", "pk_usuarios", "pk_users"),
    ("users", "uq_usuarios_email", "uq_users_email"),
    ("sources", "pk_fuentes", "pk_sources"),
    ("sources", "fk_fuentes_proceso_id", "fk_sources_process_id"),
    ("instances", "pk_instancias", "pk_instances"),
    ("instances", "fk_instancias_fichero_hash", "fk_instances_file_hash"),
    ("instances", "fk_instancias_proceso_id", "fk_instances_process_id"),
    (
        "instances",
        "uq_instancias_proceso_id_nombre_fichero_hash",
        "uq_instances_process_id_name_file_hash",
    ),
    ("symbols", "pk_simbolos", "pk_symbols"),
    ("symbols", "fk_simbolos_proceso_id", "fk_symbols_process_id"),
    ("decision_types", "pk_tipos_decision", "pk_decision_types"),
    ("decision_types", "fk_tipos_decision_proceso_id", "fk_decision_types_process_id"),
    ("decisions", "pk_decisiones", "pk_decisions"),
    ("decisions", "fk_decisiones_instancia_id", "fk_decisions_instance_id"),
    ("events", "pk_eventos", "pk_events"),
    ("events", "fk_eventos_instancia_id", "fk_events_instance_id"),
    ("extractions", "pk_extracciones", "pk_extractions"),
    ("extractions", "fk_extracciones_instancia_id", "fk_extractions_instance_id"),
    ("rules", "pk_reglas", "pk_rules"),
    ("rules", "fk_reglas_proceso_id", "fk_rules_process_id"),
    ("rules", "fk_reglas_proceso_id_decision", "fk_rules_process_id_decision"),
    ("findings", "pk_hallazgos", "pk_findings"),
    ("findings", "fk_hallazgos_decision_id", "fk_findings_decision_id"),
    ("findings", "fk_hallazgos_regla_id", "fk_findings_rule_id"),
]

# Tables whose integer `id` owns a sequence.
SERIAL = ["procesos", "usuarios", "fuentes", "instancias", "decisiones", "eventos",
          "extracciones", "reglas", "hallazgos"]  # fmt: skip

INDEXES = [
    ("ix_decisiones_instancia_id", "ix_decisions_instance_id"),
    ("ix_eventos_instancia_id", "ix_events_instance_id"),
]

# (old table, old constraint, new table, new constraint, new column, values old -> new)
CHECKS = [
    ("usuarios", "ck_usuarios_rol", "users", "ck_users_role", "role",
     {"responsable": "manager", "operador": "operator"}),
    ("instancias", "ck_instancias_estado", "instances", "ck_instances_status", "status",
     {"PENDIENTE": "PENDING", "REVISION": "REVIEW", "DECIDIDA": "DECIDED"}),
    ("reglas", "ck_reglas_tipo", "rules", "ck_rules_type", "type",
     {"requisito": "requirement", "prohibicion": "prohibition"}),
    ("reglas", "ck_reglas_estado", "rules", "ck_rules_status", "status",
     {"borrador": "draft", "rechazada": "rejected", "activa": "active", "retirada": "retired"}),
    ("decisiones", "ck_decisiones_tipo_humana", "decisions", "ck_decisions_human_kind",
     "human_kind", {"resolucion": "resolution", "correccion_revision": "review_correction"}),
]  # fmt: skip

# Values without a check constraint: (new table, new column, old -> new).
VALUES = [
    ("llm_config", "role", {
        "compilador_a": "compiler_a", "compilador_b": "compiler_b", "asistente": "assistant",
    }),
    ("decisions", "author", {"motor": "engine"}),
    ("events", "step", {
        "resolucion": "resolution", "compilar_regla": "compile_rule",
        "sugerir_escalado": "suggest_escalation",
    }),
    ("symbols", "type", {
        "texto": "text", "numero": "number", "fecha": "date", "booleano": "boolean",
    }),
    ("findings", "type", {"decision_distinta": "different_decision"}),
]  # fmt: skip

RESULT_KEYS = {"regla_id": "rule_id", "salta": "fires", "motivo": "reason"}
TEST_KEYS = {
    "nombre": "name",
    "instancia": "instance",
    "fuentes": "sources",
    "otras": "others",
    "salta": "fires",
}
REPORT_KEYS = {
    "valida": "valid",
    "historico": "history",
    "discrepancias": "discrepancies",
    "autor": "author",
    "nombre": "name",
    "esperado": "expected",
    "pasa": "passed",
    "instancias": "instances",
    "coinciden": "agree",
    "origen": "origin",  # a rule loaded with hand-written code
    "fichero": "file",
}
HAND_WRITTEN = {"escrita a mano": "hand-written"}
SYMBOL_KEYS = {"valor": "value", "origen": "origin"}
EVENT_KEYS = {
    "modelo": "model",
    "intentos": "attempts",
    "reglas_hash": "rules_hash",
    "autor": "author",
    "regla_id": "rule_id",
    "papel": "role",
    "reparaciones": "repairs",
    "valida": "valid",
}


def _keys(d: dict, keys: dict[str, str]) -> dict:
    return {keys.get(k, k): v for k, v in d.items()}


def _results(value: list, keys: dict[str, str]) -> list:
    return [_keys(r, keys) if isinstance(r, dict) else r for r in value]


def _tests(value: list, keys: dict[str, str]) -> list:
    forward = "otras" in keys
    others = "others" if forward else "otras"
    inner = {"_instancia": "_instance"} if forward else {"_instance": "_instancia"}
    out = []
    for t in value:
        if isinstance(t, dict):
            t = _keys(t, keys)
            if isinstance(t.get(others), list):
                t[others] = [_keys(o, inner) if isinstance(o, dict) else o for o in t[others]]
        out.append(t)
    return out


def _report(value: dict, keys: dict[str, str]) -> dict:
    report = _keys(value, keys)
    for k, v in report.items():
        if isinstance(v, list):
            report[k] = _results(v, keys)
        elif isinstance(v, dict):
            report[k] = _keys(v, keys)
    origin = "origin" if "valida" in keys else "origen"
    values = HAND_WRITTEN if "valida" in keys else _invert(HAND_WRITTEN)
    if report.get(origin) in values:
        report[origin] = values[report[origin]]
    return report


def _symbols(value: dict, keys: dict[str, str]) -> dict:
    return {k: _keys(v, keys) if isinstance(v, dict) else v for k, v in value.items()}


def _invert(keys: dict[str, str]) -> dict[str, str]:
    return {v: k for k, v in keys.items()}


def _rewrite_json(table: str, column: str, transform, keys: dict[str, str]) -> None:
    """Rewrite one JSONB column row by row. Tables here hold hundreds of rows, not millions."""
    conn = op.get_bind()
    rows = conn.execute(
        sa.text(f"SELECT id, {column} FROM {table} WHERE {column} IS NOT NULL")
    ).all()
    for row_id, value in rows:
        if value is None:  # JSON null
            continue
        conn.execute(
            sa.text(f"UPDATE {table} SET {column} = CAST(:v AS JSONB) WHERE id = :id"),
            {"v": json.dumps(transform(value, keys)), "id": row_id},
        )


def _rewrite_values(table: str, column: str, mapping: dict[str, str]) -> None:
    for old, new in mapping.items():
        op.execute(
            sa.text(f"UPDATE {table} SET {column} = :new WHERE {column} = :old").bindparams(
                old=old, new=new
            )
        )


JSON_COLUMNS = [
    ("decisions", "results", _results, RESULT_KEYS),
    ("rules", "tests_a", _tests, TEST_KEYS),
    ("rules", "tests_b", _tests, TEST_KEYS),
    ("rules", "report", _report, REPORT_KEYS),
    ("instances", "symbols", _symbols, SYMBOL_KEYS),
    ("extractions", "symbols", _symbols, SYMBOL_KEYS),
    ("events", "data", _keys, EVENT_KEYS),
]


def upgrade() -> None:
    for old_table, old_ck, *_ in CHECKS:
        op.drop_constraint(op.f(old_ck), old_table, type_="check")
    for old, new in TABLES.items():
        op.rename_table(old, new)
    for table, columns in COLUMNS.items():
        for old, new in columns.items():
            op.alter_column(table, old, new_column_name=new)
    for table, old, new in CONSTRAINTS:
        op.execute(f"ALTER TABLE {table} RENAME CONSTRAINT {old} TO {new}")
    for old, new in INDEXES:
        op.execute(f"ALTER INDEX {old} RENAME TO {new}")
    for old in SERIAL:
        op.execute(f"ALTER SEQUENCE {old}_id_seq RENAME TO {TABLES[old]}_id_seq")
    for _, _, table, ck, column, mapping in CHECKS:
        _rewrite_values(table, column, mapping)
        values = ", ".join(f"'{v}'" for v in mapping.values())
        op.create_check_constraint(op.f(ck), table, f"{column} in ({values})")
    for table, column, mapping in VALUES:
        _rewrite_values(table, column, mapping)
    for table, column, transform, keys in JSON_COLUMNS:
        _rewrite_json(table, column, transform, keys)


def downgrade() -> None:
    for table, column, transform, keys in JSON_COLUMNS:
        _rewrite_json(table, column, transform, _invert(keys))
    for table, column, mapping in VALUES:
        _rewrite_values(table, column, _invert(mapping))
    for _, _, table, ck, column, mapping in CHECKS:
        op.drop_constraint(op.f(ck), table, type_="check")
        _rewrite_values(table, column, _invert(mapping))
    for old, new in INDEXES:
        op.execute(f"ALTER INDEX {new} RENAME TO {old}")
    for old in SERIAL:
        op.execute(f"ALTER SEQUENCE {TABLES[old]}_id_seq RENAME TO {old}_id_seq")
    for table, old, new in CONSTRAINTS:
        op.execute(f"ALTER TABLE {table} RENAME CONSTRAINT {new} TO {old}")
    for table, columns in COLUMNS.items():
        for old, new in columns.items():
            op.alter_column(table, new, new_column_name=old)
    for old, new in TABLES.items():
        op.rename_table(new, old)
    for old_table, old_ck, _, _, old_column_of, mapping in CHECKS:
        column = _invert(COLUMNS[TABLES[old_table]])[old_column_of]
        values = ", ".join(f"'{v}'" for v in mapping)
        op.create_check_constraint(op.f(old_ck), old_table, f"{column} in ({values})")
