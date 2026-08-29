from __future__ import annotations

import re
import sqlite3
from pathlib import Path


MIGRATION_PATTERN = re.compile(r"^(\d+)_.*\.sql$")


def apply_migrations(connection: sqlite3.Connection, migrations_dir: Path) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    applied = {
        int(row["version"])
        for row in connection.execute("SELECT version FROM schema_migrations")
    }
    for path in sorted(migrations_dir.glob("*.sql")):
        match = MIGRATION_PATTERN.match(path.name)
        if not match:
            continue
        version = int(match.group(1))
        if version in applied:
            continue
        script = path.read_text(encoding="utf-8")
        try:
            connection.executescript(
                "BEGIN IMMEDIATE;\n"
                + script
                + f"\nINSERT INTO schema_migrations(version) VALUES ({version});\nCOMMIT;"
            )
        except sqlite3.DatabaseError:
            if connection.in_transaction:
                connection.rollback()
            raise
