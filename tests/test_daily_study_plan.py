from __future__ import annotations

from datetime import timedelta, timezone
from pathlib import Path

import pytest

from learning_os.database.connection import connect
from learning_os.database.daily_plan import DailyStudyPlan, DailyStudyPlanItem
from learning_os.database.migrations import apply_migrations
from learning_os.database.progress_repository import ProgressRepository


ROOT = Path(__file__).parents[1]


def repository(tmp_path: Path) -> tuple[ProgressRepository, object]:
    connection = connect(tmp_path / "learning.db")
    apply_migrations(connection, ROOT / "migrations")
    return ProgressRepository(connection), connection


def test_daily_plan_round_trip_preserves_order_and_replaces_items(
    tmp_path: Path,
) -> None:
    progress, _ = repository(tmp_path)

    saved = progress.save_daily_plan(
        "2026-08-30",
        45,
        [("pspo-i", "product-value"), ("aice-associate", "pandas-basics")],
    )

    assert saved == DailyStudyPlan(
        local_date="2026-08-30",
        available_minutes=45,
        items=(
            DailyStudyPlanItem("pspo-i", "product-value"),
            DailyStudyPlanItem("aice-associate", "pandas-basics"),
        ),
    )
    assert progress.load_daily_plan("2026-08-30") == saved

    replaced = progress.save_daily_plan(
        "2026-08-30",
        20,
        [DailyStudyPlanItem("pspo-i", "scrum-theory")],
    )

    assert progress.load_daily_plan("2026-08-30") == replaced


def test_saved_empty_daily_plan_is_distinct_from_missing_plan(tmp_path: Path) -> None:
    progress, _ = repository(tmp_path)

    assert progress.load_daily_plan("2026-08-30") is None

    progress.save_daily_plan("2026-08-30", 0, [])

    assert progress.load_daily_plan("2026-08-30") == DailyStudyPlan(
        local_date="2026-08-30",
        available_minutes=0,
        items=(),
    )


def test_completed_lesson_count_uses_requested_local_date_boundary(
    tmp_path: Path,
) -> None:
    progress, connection = repository(tmp_path)
    connection.executemany(
        """
        INSERT INTO lesson_progress(
            course_id, lesson_id, status, started_at, completed_at, last_opened_at
        ) VALUES (?, ?, 'completed', ?, ?, ?)
        """,
        [
            (
                "course",
                "before",
                "2026-08-29T14:59:59+00:00",
                "2026-08-29T14:59:59+00:00",
                "2026-08-29T14:59:59+00:00",
            ),
            (
                "course",
                "first",
                "2026-08-29T15:00:00+00:00",
                "2026-08-29T15:00:00+00:00",
                "2026-08-29T15:00:00+00:00",
            ),
            (
                "course",
                "last",
                "2026-08-30T14:59:59+00:00",
                "2026-08-30T14:59:59+00:00",
                "2026-08-30T14:59:59+00:00",
            ),
            (
                "course",
                "after",
                "2026-08-30T15:00:00+00:00",
                "2026-08-30T15:00:00+00:00",
                "2026-08-30T15:00:00+00:00",
            ),
        ],
    )
    connection.commit()

    count = progress.completed_lesson_count_on(
        "2026-08-30",
        local_timezone=timezone(timedelta(hours=9)),
    )

    assert count == 2
    assert progress.completed_lessons_on(
        "2026-08-30",
        local_timezone=timezone(timedelta(hours=9)),
    ) == (
        DailyStudyPlanItem("course", "first"),
        DailyStudyPlanItem("course", "last"),
    )


@pytest.mark.parametrize("invalid_date", ["2026-8-30", "30-08-2026", "not-a-date"])
def test_daily_plan_rejects_non_iso_local_dates(
    tmp_path: Path, invalid_date: str
) -> None:
    progress, _ = repository(tmp_path)

    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        progress.save_daily_plan(invalid_date, 30, [])


def test_daily_plan_migration_is_idempotent_and_preserves_existing_progress(
    tmp_path: Path,
) -> None:
    migration_dir = tmp_path / "migrations"
    migration_dir.mkdir()
    for name in ("001_initial.sql", "002_phase2_learning.sql"):
        (migration_dir / name).write_text(
            (ROOT / "migrations" / name).read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    connection = connect(tmp_path / "upgrade.db")
    apply_migrations(connection, migration_dir)
    ProgressRepository(connection).mark_completed("legacy", "lesson")
    (migration_dir / "003_daily_study_plan.sql").write_text(
        (ROOT / "migrations" / "003_daily_study_plan.sql").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    apply_migrations(connection, migration_dir)
    apply_migrations(connection, migration_dir)

    assert ProgressRepository(connection).statuses() == {
        ("legacy", "lesson"): "completed"
    }
    assert [
        row["version"]
        for row in connection.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        )
    ] == [1, 2, 3]
