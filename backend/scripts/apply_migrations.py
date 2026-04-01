from pathlib import Path
from typing import LiteralString, cast

import psycopg
from psycopg.connection import Connection

from config import settings

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"


def _connect() -> Connection:
    return psycopg.connect(settings.database_url)


def main() -> None:
    with _connect() as conn, conn.cursor() as cur:
        lock_acquired = False
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cur.execute("SELECT pg_advisory_lock(918273645)")
        lock_acquired = True

        try:
            for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
                version = migration.name
                cur.execute(
                    "SELECT version FROM schema_migrations WHERE version = %s",
                    (version,),
                )
                if cur.fetchone() is not None:
                    continue

                sql = migration.read_text(encoding="utf-8")
                cur.execute(cast(LiteralString, sql))
                cur.execute(
                    "INSERT INTO schema_migrations (version) VALUES (%s)",
                    (version,),
                )
                conn.commit()
        finally:
            if lock_acquired:
                cur.execute("SELECT pg_advisory_unlock(918273645)")


if __name__ == "__main__":
    main()
