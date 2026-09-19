"""Grant a non-owner runtime role access to this app only. Run with migration credentials.

TRACE_APP_DATABASE_PASSWORD must be supplied privately; no credentials are printed.
"""

import os

import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url

from app.core.config import settings
from app.features.database_api.service import READ_ONLY, names


def main() -> None:
    password = os.environ["TRACE_APP_DATABASE_PASSWORD"]
    if len(password) < 24:
        raise ValueError("Use a generated database password of at least 24 characters")
    url = make_url(settings.database_url).set(drivername="postgresql")
    role = sql.Identifier("trace_app")
    with psycopg.connect(url.render_as_string(hide_password=False)) as connection:
        if not connection.execute("SELECT 1 FROM pg_roles WHERE rolname='trace_app'").fetchone():
            connection.execute(sql.SQL("CREATE ROLE {} LOGIN").format(role))
        connection.execute(
            sql.SQL(
                "ALTER ROLE {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION "
                "NOBYPASSRLS PASSWORD {}"
            ).format(role, sql.Literal(password))
        )
        connection.execute(
            sql.SQL("REVOKE ALL ON DATABASE {} FROM {}").format(sql.Identifier(url.database), role)
        )
        connection.execute(
            sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(sql.Identifier(url.database), role)
        )
        connection.execute(sql.SQL("REVOKE ALL ON SCHEMA public FROM {}").format(role))
        connection.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(role))
        # Remove old grants before granting exactly the current application allowlist.
        connection.execute(
            sql.SQL("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {}").format(role)
        )
        connection.execute(
            sql.SQL("REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM {}").format(role)
        )
        for name in names():
            if name in {"events", "mail_activity"}:
                permissions = "SELECT, INSERT, DELETE"
            else:
                permissions = (
                    "SELECT, INSERT"
                    if name in READ_ONLY
                    else "SELECT, INSERT, UPDATE, DELETE"
                )
            connection.execute(
                sql.SQL("GRANT {} ON TABLE public.{} TO {}").format(
                    sql.SQL(permissions), sql.Identifier(name), role
                )
            )
            sequences = connection.execute(
                "SELECT pg_get_serial_sequence(format('public.%%I', table_name), column_name) "
                "FROM information_schema.columns WHERE table_schema='public' AND table_name=%s",
                (name,),
            ).fetchall()
            for (sequence,) in sequences:
                if sequence:
                    # pg_get_serial_sequence returns a server-quoted qualified identifier.
                    connection.execute(
                        sql.SQL("GRANT USAGE, SELECT ON SEQUENCE {} TO {}").format(
                            sql.SQL(sequence), role
                        )
                    )
    print("Restricted trace_app grants refreshed for registered Trace-it tables.")


if __name__ == "__main__":
    main()
