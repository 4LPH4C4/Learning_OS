from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    project_root: Path = PROJECT_ROOT
    courses_dir: Path = PROJECT_ROOT / "courses"
    data_dir: Path = PROJECT_ROOT / "data"
    external_dir: Path = PROJECT_ROOT / "external"
    migrations_dir: Path = PROJECT_ROOT / "migrations"
    database_path: Path = PROJECT_ROOT / "data" / "learning_os.db"
    default_study_minutes: int = 60


def load_settings(project_root: Path | None = None) -> Settings:
    if project_root is None:
        return Settings()
    root = project_root.resolve()
    return Settings(
        project_root=root,
        courses_dir=root / "courses",
        data_dir=root / "data",
        external_dir=root / "external",
        migrations_dir=root / "migrations",
        database_path=root / "data" / "learning_os.db",
    )
