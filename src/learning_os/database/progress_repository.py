from __future__ import annotations

import sqlite3
from datetime import date, datetime, time, timezone, tzinfo
from pathlib import Path
from typing import Iterable

from learning_os.core.models import Course, SourceState
from learning_os.database.daily_plan import DailyStudyPlan, DailyStudyPlanItem


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _parse_local_date(value: str) -> date:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise ValueError("local_date must use YYYY-MM-DD format") from error
    if parsed.isoformat() != value:
        raise ValueError("local_date must use YYYY-MM-DD format")
    return parsed


class ProgressRepository:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def register_courses(self, courses: Iterable[Course]) -> None:
        now = utc_now()
        with self.connection:
            self.connection.executemany(
                """
                INSERT INTO course_registrations(
                    course_id, schema_version, manifest_hash, title, status, last_seen_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(course_id) DO UPDATE SET
                    schema_version=excluded.schema_version,
                    manifest_hash=excluded.manifest_hash,
                    title=excluded.title,
                    status=excluded.status,
                    last_seen_at=excluded.last_seen_at
                """,
                [
                    (
                        course.id,
                        course.schema_version,
                        course.manifest_hash,
                        course.title,
                        course.status,
                        now,
                    )
                    for course in courses
                ],
            )

    def statuses(self) -> dict[tuple[str, str], str]:
        return {
            (str(row["course_id"]), str(row["lesson_id"])): str(row["status"])
            for row in self.connection.execute(
                "SELECT course_id, lesson_id, status FROM lesson_progress"
            )
        }

    def mark_started(self, course_id: str, lesson_id: str) -> None:
        now = utc_now()
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO lesson_progress(
                    course_id, lesson_id, status, started_at, completed_at, last_opened_at
                ) VALUES (?, ?, 'started', ?, NULL, ?)
                ON CONFLICT(course_id, lesson_id) DO UPDATE SET
                    status=CASE
                        WHEN lesson_progress.status='completed' THEN 'completed'
                        ELSE 'started'
                    END,
                    started_at=COALESCE(lesson_progress.started_at, excluded.started_at),
                    last_opened_at=excluded.last_opened_at
                """,
                (course_id, lesson_id, now, now),
            )

    def mark_completed(self, course_id: str, lesson_id: str) -> None:
        now = utc_now()
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO lesson_progress(
                    course_id, lesson_id, status, started_at, completed_at, last_opened_at
                ) VALUES (?, ?, 'completed', ?, ?, ?)
                ON CONFLICT(course_id, lesson_id) DO UPDATE SET
                    status='completed',
                    started_at=COALESCE(lesson_progress.started_at, excluded.started_at),
                    completed_at=COALESCE(lesson_progress.completed_at, excluded.completed_at),
                    last_opened_at=excluded.last_opened_at
                """,
                (course_id, lesson_id, now, now, now),
            )

    def progress_for(self, course: Course) -> tuple[int, int]:
        required = course.required_lessons
        statuses = self.statuses()
        completed = sum(
            1
            for lesson in required
            if statuses.get((course.id, lesson.id)) == "completed"
        )
        return completed, len(required)

    def save_daily_plan(
        self,
        local_date: str,
        available_minutes: int,
        items: Iterable[DailyStudyPlanItem | tuple[str, str]],
    ) -> DailyStudyPlan:
        _parse_local_date(local_date)
        if available_minutes < 0:
            raise ValueError("available_minutes must be zero or greater")

        normalized_items = tuple(
            item
            if isinstance(item, DailyStudyPlanItem)
            else DailyStudyPlanItem(course_id=item[0], lesson_id=item[1])
            for item in items
        )
        if any(not item.course_id or not item.lesson_id for item in normalized_items):
            raise ValueError("course_id and lesson_id must not be empty")

        now = utc_now()
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO daily_study_plans(
                    local_date, available_minutes, created_at, updated_at
                ) VALUES (?, ?, ?, ?)
                ON CONFLICT(local_date) DO UPDATE SET
                    available_minutes=excluded.available_minutes,
                    updated_at=excluded.updated_at
                """,
                (local_date, available_minutes, now, now),
            )
            self.connection.execute(
                "DELETE FROM daily_study_plan_items WHERE local_date=?",
                (local_date,),
            )
            self.connection.executemany(
                """
                INSERT INTO daily_study_plan_items(
                    local_date, position, course_id, lesson_id
                ) VALUES (?, ?, ?, ?)
                """,
                [
                    (local_date, position, item.course_id, item.lesson_id)
                    for position, item in enumerate(normalized_items)
                ],
            )

        return DailyStudyPlan(local_date, available_minutes, normalized_items)

    def load_daily_plan(self, local_date: str) -> DailyStudyPlan | None:
        _parse_local_date(local_date)
        row = self.connection.execute(
            """
            SELECT available_minutes
            FROM daily_study_plans
            WHERE local_date=?
            """,
            (local_date,),
        ).fetchone()
        if row is None:
            return None

        items = tuple(
            DailyStudyPlanItem(
                course_id=str(item["course_id"]),
                lesson_id=str(item["lesson_id"]),
            )
            for item in self.connection.execute(
                """
                SELECT course_id, lesson_id
                FROM daily_study_plan_items
                WHERE local_date=?
                ORDER BY position
                """,
                (local_date,),
            )
        )
        return DailyStudyPlan(local_date, int(row["available_minutes"]), items)

    def completed_lesson_count_on(
        self,
        local_date: str,
        *,
        local_timezone: tzinfo | None = None,
    ) -> int:
        parsed_date = _parse_local_date(local_date)
        resolved_timezone = local_timezone or datetime.now().astimezone().tzinfo
        if resolved_timezone is None:  # pragma: no cover - defensive platform fallback
            resolved_timezone = timezone.utc
        start = datetime.combine(parsed_date, time.min, tzinfo=resolved_timezone)
        next_date = date.fromordinal(parsed_date.toordinal() + 1)
        end = datetime.combine(next_date, time.min, tzinfo=resolved_timezone)
        start_utc = start.astimezone(timezone.utc).isoformat(timespec="seconds")
        end_utc = end.astimezone(timezone.utc).isoformat(timespec="seconds")
        row = self.connection.execute(
            """
            SELECT COUNT(*) AS completed_count
            FROM lesson_progress
            WHERE status='completed'
              AND completed_at >= ?
              AND completed_at < ?
            """,
            (start_utc, end_utc),
        ).fetchone()
        return int(row["completed_count"])

    def completed_lessons_on(
        self,
        local_date: str,
        *,
        local_timezone: tzinfo | None = None,
    ) -> tuple[DailyStudyPlanItem, ...]:
        parsed_date = _parse_local_date(local_date)
        resolved_timezone = local_timezone or datetime.now().astimezone().tzinfo
        if resolved_timezone is None:  # pragma: no cover - defensive platform fallback
            resolved_timezone = timezone.utc
        start = datetime.combine(parsed_date, time.min, tzinfo=resolved_timezone)
        next_date = date.fromordinal(parsed_date.toordinal() + 1)
        end = datetime.combine(next_date, time.min, tzinfo=resolved_timezone)
        start_utc = start.astimezone(timezone.utc).isoformat(timespec="seconds")
        end_utc = end.astimezone(timezone.utc).isoformat(timespec="seconds")
        return tuple(
            DailyStudyPlanItem(
                course_id=str(row["course_id"]),
                lesson_id=str(row["lesson_id"]),
            )
            for row in self.connection.execute(
                """
                SELECT course_id, lesson_id
                FROM lesson_progress
                WHERE status='completed'
                  AND completed_at >= ?
                  AND completed_at < ?
                ORDER BY completed_at, course_id, lesson_id
                """,
                (start_utc, end_utc),
            )
        )

    def start_session(self, course_id: str, lesson_id: str) -> int:
        now = utc_now()
        with self.connection:
            cursor = self.connection.execute(
                """
                INSERT INTO study_sessions(course_id, lesson_id, started_at, status)
                VALUES (?, ?, ?, 'active')
                """,
                (course_id, lesson_id, now),
            )
        return int(cursor.lastrowid)

    def complete_session(self, session_id: int) -> None:
        row = self.connection.execute(
            "SELECT started_at FROM study_sessions WHERE id=?", (session_id,)
        ).fetchone()
        if row is None:
            return
        ended_at = datetime.now(timezone.utc)
        started_at = datetime.fromisoformat(str(row["started_at"]))
        duration = max(0.0, (ended_at - started_at).total_seconds() / 60)
        with self.connection:
            self.connection.execute(
                """
                UPDATE study_sessions
                SET ended_at=?, duration_minutes=?, status='completed'
                WHERE id=? AND status='active'
                """,
                (ended_at.isoformat(timespec="seconds"), duration, session_id),
            )

    def save_source_state(self, state: SourceState) -> None:
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO source_repositories(
                    source_id, course_id, repo_url, local_path, commit_sha,
                    last_sync_at, status, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_id, course_id) DO UPDATE SET
                    repo_url=excluded.repo_url,
                    local_path=excluded.local_path,
                    commit_sha=excluded.commit_sha,
                    last_sync_at=excluded.last_sync_at,
                    status=excluded.status,
                    error_message=excluded.error_message
                """,
                (
                    state.source_id,
                    state.course_id,
                    state.repository_url or "",
                    str(state.local_path),
                    state.commit_sha,
                    state.last_sync_at,
                    state.status,
                    state.error_message,
                ),
            )

    def load_source_state(self, course_id: str, source_id: str) -> SourceState | None:
        row = self.connection.execute(
            """
            SELECT * FROM source_repositories WHERE course_id=? AND source_id=?
            """,
            (course_id, source_id),
        ).fetchone()
        if row is None:
            return None
        return SourceState(
            source_id=str(row["source_id"]),
            course_id=str(row["course_id"]),
            status=str(row["status"]),
            local_path=Path(str(row["local_path"])),
            repository_url=str(row["repo_url"]),
            commit_sha=row["commit_sha"],
            last_sync_at=row["last_sync_at"],
            error_message=row["error_message"],
            available=str(row["status"]) == "ready",
        )
