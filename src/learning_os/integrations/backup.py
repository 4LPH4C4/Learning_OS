"""Safe, local-only SQLite backup and restore utilities."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class BackupError(RuntimeError):
    """Raised when a backup is invalid or cannot be safely restored."""

    def __init__(self, message: str, *, safety_backup_path: Path | None = None):
        super().__init__(message)
        self.safety_backup_path = safety_backup_path


@dataclass(frozen=True)
class BackupInfo:
    path: Path
    created_at: str
    database_size: int
    schema_versions: tuple[int, ...]
    manifest: dict[str, Any]

    @property
    def size_bytes(self) -> int:
        return self.database_size


class BackupManager:
    def __init__(self, data_dir: Path, database_path: Path):
        self.data_dir = Path(data_dir).resolve()
        self.database_path = Path(database_path).resolve()
        self.backups_dir = (self.data_dir / "backups").resolve()
        self.backups_dir.mkdir(parents=True, exist_ok=True)

    def _backup_path(self, path: Path) -> Path:
        candidate = Path(path).resolve()
        try:
            candidate.relative_to(self.backups_dir)
        except ValueError as exc:
            raise BackupError("백업 경로는 data/backups 안에 있어야 한다") from exc
        if candidate == self.backups_dir:
            raise BackupError("백업 파일 경로가 필요하다")
        return candidate

    def _temporary_dir(self) -> Path:
        return Path(tempfile.mkdtemp(prefix="learning_os_backup_", dir=self.data_dir))

    def create_backup(self) -> Path:
        if not self.database_path.is_file():
            raise BackupError(f"SQLite DB를 찾을 수 없다: {self.database_path}")
        temp_dir = self._temporary_dir()
        try:
            snapshot = temp_dir / "learning_os.db"
            try:
                source = sqlite3.connect(str(self.database_path), uri=False)
                destination = sqlite3.connect(str(snapshot))
                try:
                    source.backup(destination)
                    destination.commit()
                finally:
                    destination.close()
                    source.close()
            except sqlite3.DatabaseError as exc:
                raise BackupError("SQLite snapshot 생성에 실패했다") from exc

            created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
            digest = hashlib.sha256(snapshot.read_bytes()).hexdigest()
            connection = sqlite3.connect(str(snapshot))
            try:
                versions = tuple(
                    int(row[0])
                    for row in connection.execute(
                        "SELECT version FROM schema_migrations ORDER BY version"
                    )
                ) if self._table_exists(connection, "schema_migrations") else ()
            finally:
                connection.close()
            manifest = {
                "format_version": 1,
                "created_at": created_at,
                "database_file": "learning_os.db",
                "database_size": snapshot.stat().st_size,
                "database_sha256": digest,
                "schema_versions": list(versions),
            }
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            target = self.backups_dir / f"learning_os_{stamp}.zip"
            # Timestamp collisions are possible during automated tests.
            suffix = 1
            while target.exists():
                target = self.backups_dir / f"learning_os_{stamp}_{suffix}.zip"
                suffix += 1
            with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("manifest.json", json.dumps(manifest, indent=2) + "\n")
                archive.write(snapshot, "learning_os.db")
            return target
        except BackupError:
            raise
        except (OSError, zipfile.BadZipFile, sqlite3.DatabaseError) as exc:
            raise BackupError("백업 생성에 실패했다") from exc
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    @staticmethod
    def _table_exists(connection: sqlite3.Connection, name: str) -> bool:
        return connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
        ).fetchone() is not None

    def inspect(self, path: Path) -> BackupInfo:
        archive_path = self._backup_path(path)
        if not archive_path.is_file():
            raise BackupError(f"백업 파일을 찾을 수 없다: {archive_path}")
        temp_dir = self._temporary_dir()
        try:
            try:
                with zipfile.ZipFile(archive_path) as archive:
                    names = archive.namelist()
                    for name in names:
                        item = Path(name)
                        if item.is_absolute() or ".." in item.parts or name.endswith("/"):
                            raise BackupError("안전하지 않은 ZIP 경로가 포함되어 있다")
                    if set(names) != {"manifest.json", "learning_os.db"}:
                        raise BackupError("manifest.json과 learning_os.db만 포함해야 한다")
                    try:
                        manifest = json.loads(archive.read("manifest.json"))
                    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                        raise BackupError("manifest.json 형식이 올바르지 않다") from exc
                    database_bytes = archive.read("learning_os.db")
            except zipfile.BadZipFile as exc:
                raise BackupError("유효한 ZIP 백업이 아니다") from exc
            if not isinstance(manifest, dict) or manifest.get("format_version") != 1:
                raise BackupError("지원하지 않는 backup manifest format이다")
            if manifest.get("database_file") != "learning_os.db":
                raise BackupError("manifest의 database_file이 올바르지 않다")
            if manifest.get("database_size") != len(database_bytes):
                raise BackupError("백업 DB 크기가 manifest와 다르다")
            if manifest.get("database_sha256") != hashlib.sha256(database_bytes).hexdigest():
                raise BackupError("백업 DB checksum이 manifest와 다르다")
            created_at = manifest.get("created_at")
            if not isinstance(created_at, str) or not created_at:
                raise BackupError("manifest의 created_at이 필요하다")
            versions_raw = manifest.get("schema_versions", [])
            if not isinstance(versions_raw, list) or any(not isinstance(v, int) for v in versions_raw):
                raise BackupError("manifest의 schema_versions가 올바르지 않다")
            snapshot = temp_dir / "learning_os.db"
            snapshot.write_bytes(database_bytes)
            connection = sqlite3.connect(str(snapshot))
            try:
                result = connection.execute("PRAGMA integrity_check").fetchone()
                if not result or result[0] != "ok":
                    raise BackupError("백업 DB integrity_check가 실패했다")
                if not self._table_exists(connection, "schema_migrations"):
                    raise BackupError("백업 DB에 schema_migrations가 없다")
            finally:
                connection.close()
            return BackupInfo(archive_path, created_at, len(database_bytes), tuple(versions_raw), manifest)
        except OSError as exc:
            raise BackupError("백업 검사에 실패했다") from exc
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def restore(self, path: Path) -> Path:
        safety: Path | None = None
        try:
            safety = self.create_backup()
            info = self.inspect(path)
            temp_dir = self._temporary_dir()
            try:
                restored = temp_dir / "learning_os.db"
                with zipfile.ZipFile(info.path) as archive, archive.open("learning_os.db") as source:
                    with restored.open("wb") as destination:
                        shutil.copyfileobj(source, destination)
                # inspect already validated the bytes; use replace only after complete extraction.
                self.database_path.parent.mkdir(parents=True, exist_ok=True)
                for suffix in ("-wal", "-shm"):
                    sidecar = Path(f"{self.database_path}{suffix}")
                    if sidecar.exists():
                        sidecar.unlink()
                os.replace(restored, self.database_path)
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)
            return safety
        except BackupError as exc:
            if exc.safety_backup_path is None:
                exc.safety_backup_path = safety
            raise
        except (OSError, zipfile.BadZipFile, sqlite3.DatabaseError) as exc:
            raise BackupError("복원에 실패했다", safety_backup_path=safety) from exc
