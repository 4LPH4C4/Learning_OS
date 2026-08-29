from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from learning_os.core.catalog import discover_courses
from learning_os.core.manifests import ManifestError, load_manifest
from learning_os.core.models import SourceState
from learning_os.core.today import build_today_plan
from learning_os.database.connection import connect
from learning_os.database.migrations import apply_migrations
from learning_os.database.progress_repository import ProgressRepository
from learning_os.integrations.content_loader import read_markdown


MANIFEST = """\
schema_version: 1
id: {course_id}
title: {title}
description: A test course
category: testing
source_type: local
schedule:
  target_date: 2026-10-30
  priority: {priority}
content_sources:
  - id: local-content
    type: local
    base_path: content
modules:
  - id: basics
    title: Basics
    order: 1
    lessons:
      - id: first-lesson
        title: First lesson
        type: markdown
        duration_minutes: 20
        content_path: first.md
      - id: second-lesson
        title: Second lesson
        type: markdown
        duration_minutes: 50
        content_path: second.md
completion_criteria:
  type: all_required_lessons
"""


def write_course(root: Path, course_id: str, *, title: str | None = None, priority: int = 0) -> Path:
    course_root = root / course_id
    (course_root / "content").mkdir(parents=True)
    (course_root / "content" / "first.md").write_text("# First", encoding="utf-8")
    (course_root / "content" / "second.md").write_text("# Second", encoding="utf-8")
    (course_root / "course.yaml").write_text(
        MANIFEST.format(course_id=course_id, title=title or course_id.title(), priority=priority),
        encoding="utf-8",
    )
    return course_root


def prepare_db(tmp_path: Path) -> tuple[sqlite3.Connection, ProgressRepository]:
    connection = connect(tmp_path / "data" / "learning.db")
    apply_migrations(connection, Path(__file__).parents[1] / "migrations")
    return connection, ProgressRepository(connection)


def test_valid_manifest_loading_reads_course_structure(tmp_path: Path) -> None:
    course_root = write_course(tmp_path, "valid-course", title="Valid Course", priority=3)

    course = load_manifest(course_root / "course.yaml")

    assert course.id == "valid-course"
    assert course.title == "Valid Course"
    assert course.schedule.priority == 3
    assert [lesson.id for lesson in course.lessons] == ["first-lesson", "second-lesson"]
    assert course.lessons[0].course_root == course_root.resolve()
    assert course.manifest_hash


def test_malformed_manifest_isolated_as_catalog_issue(tmp_path: Path) -> None:
    courses_dir = tmp_path / "courses"
    write_course(courses_dir, "good-course")
    bad = courses_dir / "bad-course"
    bad.mkdir(parents=True)
    (bad / "course.yaml").write_text("schema_version: 1\nid: BAD ID\n", encoding="utf-8")

    catalog = discover_courses(courses_dir)

    assert [course.id for course in catalog.courses] == ["good-course"]
    assert len(catalog.issues) == 1
    assert catalog.issues[0].manifest_path == (bad / "course.yaml").resolve()
    assert "course.id" in catalog.issues[0].message


@pytest.mark.parametrize(
    ("replacement", "message"),
    [
        ("priority: invalid", "course.schedule.priority"),
        ("content_sources:\n  - invalid", "course.content_sources[0]"),
    ],
)
def test_structurally_invalid_manifest_isolated_as_catalog_issue(
    tmp_path: Path,
    replacement: str,
    message: str,
) -> None:
    courses_dir = tmp_path / "courses"
    write_course(courses_dir, "good-course")
    bad = write_course(courses_dir, "bad-course")
    manifest = (bad / "course.yaml").read_text(encoding="utf-8")
    if replacement.startswith("priority"):
        manifest = manifest.replace("priority: 0", replacement)
    else:
        manifest = manifest.replace(
            "content_sources:\n  - id: local-content\n    type: local\n    base_path: content",
            replacement,
        )
    (bad / "course.yaml").write_text(manifest, encoding="utf-8")

    catalog = discover_courses(courses_dir)

    assert [course.id for course in catalog.courses] == ["good-course"]
    assert len(catalog.issues) == 1
    assert message in catalog.issues[0].message


def test_local_source_base_path_is_used_for_content_resolution(tmp_path: Path) -> None:
    course_root = write_course(tmp_path, "base-path-course")
    course = load_manifest(course_root / "course.yaml")

    assert read_markdown(course, course.lessons[0], tmp_path / "external") == "# First"


@pytest.mark.parametrize("field", ["base_path", "content_path"])
def test_manifest_rejects_path_traversal(tmp_path: Path, field: str) -> None:
    course_root = write_course(tmp_path, "safe-course")
    manifest = (course_root / "course.yaml").read_text(encoding="utf-8")
    manifest = manifest.replace(
        "content_path: first.md" if field == "content_path" else "base_path: content",
        "content_path: ../outside.md" if field == "content_path" else "base_path: ../outside",
    )
    (course_root / "course.yaml").write_text(manifest, encoding="utf-8")

    with pytest.raises(ManifestError, match="Course 폴더 밖 경로"):
        load_manifest(course_root / "course.yaml")


def test_today_plan_is_deterministic_and_uses_shortest_fallback(tmp_path: Path) -> None:
    first = load_manifest(write_course(tmp_path / "courses", "alpha", priority=1) / "course.yaml")
    second = load_manifest(write_course(tmp_path / "courses", "beta", priority=2) / "course.yaml")
    progress = {}

    plan = build_today_plan([first, second], progress, available_minutes=10, max_lessons=3)
    repeated = build_today_plan([first, second], progress, available_minutes=10, max_lessons=3)

    assert plan == repeated
    assert len(plan) == 1
    assert plan[0].course.id == "beta"
    assert plan[0].lesson.id == "first-lesson"


def test_today_plan_respects_budget_and_max_lessons(tmp_path: Path) -> None:
    courses = [
        load_manifest(write_course(tmp_path / "courses", course_id, priority=priority) / "course.yaml")
        for course_id, priority in (("one", 2), ("two", 1), ("three", 0), ("four", -1))
    ]

    plan = build_today_plan(courses, {}, available_minutes=40, max_lessons=3)

    assert [item.course.id for item in plan] == ["one", "two"]
    assert sum(item.lesson.duration_minutes for item in plan) <= 40


def test_migrations_are_idempotent(tmp_path: Path) -> None:
    connection = connect(tmp_path / "learning.db")
    migrations = Path(__file__).parents[1] / "migrations"

    apply_migrations(connection, migrations)
    apply_migrations(connection, migrations)

    assert [row["version"] for row in connection.execute("SELECT version FROM schema_migrations")] == [1]
    assert connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='study_sessions'").fetchone()


def test_progress_mark_started_and_completed_are_idempotent(tmp_path: Path) -> None:
    connection, repository = prepare_db(tmp_path)

    repository.mark_started("course", "lesson")
    repository.mark_started("course", "lesson")
    assert repository.statuses() == {("course", "lesson"): "started"}
    started_at = connection.execute("SELECT started_at FROM lesson_progress").fetchone()[0]

    repository.mark_completed("course", "lesson")
    repository.mark_completed("course", "lesson")
    repository.mark_started("course", "lesson")
    row = connection.execute("SELECT * FROM lesson_progress").fetchone()
    assert row["status"] == "completed"
    assert row["started_at"] == started_at
    assert row["completed_at"]
    assert connection.execute("SELECT COUNT(*) FROM lesson_progress").fetchone()[0] == 1


def test_course_progress_counts_required_lessons(tmp_path: Path) -> None:
    connection, repository = prepare_db(tmp_path)
    course = load_manifest(write_course(tmp_path / "courses", "progress-course") / "course.yaml")
    repository.mark_completed(course.id, "first-lesson")

    assert repository.progress_for(course) == (1, 2)


def test_progress_and_source_state_persist_across_reconnection(tmp_path: Path) -> None:
    database = tmp_path / "persistent.db"
    first_connection = connect(database)
    apply_migrations(first_connection, Path(__file__).parents[1] / "migrations")
    first_repository = ProgressRepository(first_connection)
    first_repository.mark_completed("course", "lesson")
    first_repository.save_source_state(
        SourceState(
            source_id="source", course_id="course", status="ready", local_path=tmp_path / "external",
            repository_url="https://example.test/repo", commit_sha="abc123", last_sync_at="2026-08-29T00:00:00+00:00",
        )
    )
    first_connection.close()

    second_connection = connect(database)
    second_repository = ProgressRepository(second_connection)
    assert second_repository.statuses() == {("course", "lesson"): "completed"}
    state = second_repository.load_source_state("course", "source")
    assert state is not None and state.commit_sha == "abc123" and state.available


def test_study_session_records_completion_and_is_idempotent(tmp_path: Path) -> None:
    connection, repository = prepare_db(tmp_path)

    session_id = repository.start_session("course", "lesson")
    repository.complete_session(session_id)
    repository.complete_session(session_id)
    row = connection.execute("SELECT * FROM study_sessions WHERE id=?", (session_id,)).fetchone()

    assert row["status"] == "completed"
    assert row["ended_at"]
    assert row["duration_minutes"] >= 0
    assert connection.execute("SELECT COUNT(*) FROM study_sessions").fetchone()[0] == 1
