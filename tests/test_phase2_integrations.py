import sqlite3
import zipfile
from pathlib import Path

import pytest

from learning_os.integrations.ai_provider import AIContext, AIProviderError, DisabledAIProvider
from learning_os.integrations.backup import BackupError, BackupManager


def make_db(path: Path, value: str = "before") -> None:
    db = sqlite3.connect(path)
    try:
        db.executescript(
            "CREATE TABLE schema_migrations(version INTEGER PRIMARY KEY);"
            "CREATE TABLE state(value TEXT);"
            "INSERT INTO schema_migrations VALUES (1);"
        )
        db.execute("INSERT INTO state VALUES (?)", (value,))
        db.commit()
    finally:
        db.close()


def test_backup_snapshot_inspect_and_restore(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    database = data_dir / "learning_os.db"
    database.parent.mkdir()
    make_db(database)
    manager = BackupManager(data_dir, database)

    archive = manager.create_backup()
    info = manager.inspect(archive)
    assert info.path == archive.resolve()
    assert info.schema_versions == (1,)
    db = sqlite3.connect(database)
    try:
        assert db.execute("SELECT value FROM state").fetchone()[0] == "before"
    finally:
        db.close()

    db = sqlite3.connect(database)
    try:
        db.execute("UPDATE state SET value='changed'")
        db.commit()
    finally:
        db.close()
    safety = manager.restore(archive)
    assert safety.exists()
    db = sqlite3.connect(database)
    try:
        assert db.execute("SELECT value FROM state").fetchone()[0] == "before"
    finally:
        db.close()


def test_inspect_rejects_zip_traversal(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    manager = BackupManager(data_dir, data_dir / "learning_os.db")
    archive = manager.backups_dir / "evil.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("../escape", "bad")
    with pytest.raises(BackupError):
        manager.inspect(archive)


def test_restore_invalid_archive_keeps_database(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    database = data_dir / "learning_os.db"
    database.parent.mkdir()
    make_db(database)
    archive = data_dir / "outside.zip"
    archive.write_bytes(b"not a zip")
    manager = BackupManager(data_dir, database)
    with pytest.raises(BackupError):
        manager.restore(archive)
    with sqlite3.connect(database) as db:
        assert db.execute("SELECT value FROM state").fetchone()[0] == "before"


def test_disabled_ai_provider_is_importable_and_actionable() -> None:
    with pytest.raises(AIProviderError, match="API 키"):
        DisabledAIProvider().answer(AIContext(prompt="도와줘"))
