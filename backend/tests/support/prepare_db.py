"""Recreate the test database, empty: `python -m tests.support.prepare_db`.

Reads TRACE_DATABASE_URL. Tests get their own database so they never write into the one
`make setup` fills for the demo, and it starts empty each run so a migration applied by
another branch cannot get in the way. Exits 1 if the Postgres server is not reachable.
"""

import sys

import psycopg
from sqlalchemy.engine import make_url

from app.core.config import settings


def main() -> None:
    url = make_url(settings.database_url)
    if url.database in ("trace", "postgres"):
        sys.exit(f"Refusing to recreate {url.database!r}: point TRACE_DATABASE_URL at a test db")
    server = url.set(drivername="postgresql", database="postgres").render_as_string(
        hide_password=False
    )
    try:
        with psycopg.connect(server, autocommit=True, connect_timeout=3) as conn:
            conn.execute(f'DROP DATABASE IF EXISTS "{url.database}" WITH (FORCE)')
            conn.execute(f'CREATE DATABASE "{url.database}"')
    except psycopg.OperationalError as error:
        sys.exit(f"Postgres not reachable at {url.host}:{url.port}: {error}")


if __name__ == "__main__":
    main()
