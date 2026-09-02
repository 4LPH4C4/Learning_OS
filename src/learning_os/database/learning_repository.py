from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone, tzinfo
from typing import Iterable, Sequence

from learning_os.core.assessment import QuizQuestion, ReviewSchedule
from learning_os.core.insights import Note, StudyActivity, StudySummary, TopicInsight
from learning_os.core.mastery import SkillEvidence, SkillMastery, calculate_all_mastery
from learning_os.core.models import Course
from learning_os.core.review import schedule_review
from learning_os.database.progress_repository import utc_now


class LearningRepository:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def sync_catalog(
        self,
        courses: Iterable[Course],
        questions: Iterable[QuizQuestion],
    ) -> None:
        course_items = tuple(courses)
        question_items = tuple(questions)
        skill_ids = {
            skill
            for course in course_items
            for skill in (
                *course.skills,
                *(skill for lesson in course.lessons for skill in lesson.skills),
            )
        }
        skill_ids.update(question.skill_id for question in question_items)
        course_ids = tuple(course.id for course in course_items)
        now = utc_now()
        with self.connection:
            self.connection.executemany(
                """
                INSERT INTO skills(skill_id, title, description, updated_at)
                VALUES (?, ?, '', ?)
                ON CONFLICT(skill_id) DO UPDATE SET
                    title=excluded.title,
                    updated_at=excluded.updated_at
                """,
                [
                    (skill_id, skill_id.replace("-", " ").title(), now)
                    for skill_id in sorted(skill_ids)
                ],
            )
            if course_ids:
                placeholders = ", ".join("?" for _ in course_ids)
                self.connection.execute(
                    f"DELETE FROM lesson_skills WHERE course_id IN ({placeholders})",
                    course_ids,
                )
                self.connection.execute(
                    f"UPDATE quiz_questions SET active=0, updated_at=? "
                    f"WHERE course_id IN ({placeholders})",
                    (now, *course_ids),
                )
            self.connection.executemany(
                """
                INSERT OR IGNORE INTO lesson_skills(course_id, lesson_id, skill_id)
                VALUES (?, ?, ?)
                """,
                [
                    (course.id, lesson.id, skill_id)
                    for course in course_items
                    for lesson in course.lessons
                    for skill_id in lesson.skills
                ],
            )
            self.connection.executemany(
                """
                INSERT INTO quiz_questions(
                    course_id, question_id, lesson_id, skill_id, topic, difficulty,
                    question_type, prompt, options_json, correct_answers_json,
                    explanation, incorrect_explanations_json, source_ref,
                    content_hash, active, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                ON CONFLICT(course_id, question_id) DO UPDATE SET
                    lesson_id=excluded.lesson_id,
                    skill_id=excluded.skill_id,
                    topic=excluded.topic,
                    difficulty=excluded.difficulty,
                    question_type=excluded.question_type,
                    prompt=excluded.prompt,
                    options_json=excluded.options_json,
                    correct_answers_json=excluded.correct_answers_json,
                    explanation=excluded.explanation,
                    incorrect_explanations_json=excluded.incorrect_explanations_json,
                    source_ref=excluded.source_ref,
                    content_hash=excluded.content_hash,
                    active=1,
                    updated_at=excluded.updated_at
                """,
                [
                    (
                        question.course_id,
                        question.id,
                        question.lesson_id,
                        question.skill_id,
                        question.topic,
                        question.difficulty,
                        question.type,
                        question.prompt,
                        json.dumps(
                            [{"id": option.id, "text": option.text} for option in question.options],
                            ensure_ascii=False,
                        ),
                        json.dumps(question.correct_answers, ensure_ascii=False),
                        question.explanation,
                        json.dumps(dict(question.incorrect_explanations), ensure_ascii=False),
                        question.source_ref,
                        question.content_hash,
                        now,
                    )
                    for question in question_items
                ],
            )

    def record_attempt(
        self,
        question: QuizQuestion,
        answers: Sequence[str],
        *,
        correct: bool,
        response_time_seconds: float,
        confidence: int,
        today: date | None = None,
    ) -> tuple[int, ReviewSchedule]:
        if not 1 <= confidence <= 5:
            raise ValueError("confidence는 1~5여야 한다")
        previous = self.connection.execute(
            "SELECT streak FROM review_schedule WHERE course_id=? AND question_id=?",
            (question.course_id, question.id),
        ).fetchone()
        next_review = schedule_review(
            correct=correct,
            confidence=confidence,
            previous_streak=int(previous["streak"]) if previous else 0,
            today=today,
        )
        now = utc_now()
        with self.connection:
            cursor = self.connection.execute(
                """
                INSERT INTO quiz_attempts(
                    course_id, question_id, skill_id, topic, answer_json,
                    is_correct, response_time_seconds, confidence, attempted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    question.course_id,
                    question.id,
                    question.skill_id,
                    question.topic,
                    json.dumps(tuple(answers), ensure_ascii=False),
                    int(correct),
                    max(0.0, float(response_time_seconds)),
                    confidence,
                    now,
                ),
            )
            self.connection.execute(
                """
                INSERT INTO review_schedule(
                    course_id, question_id, due_on, interval_days, streak,
                    last_correct, last_confidence, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(course_id, question_id) DO UPDATE SET
                    due_on=excluded.due_on,
                    interval_days=excluded.interval_days,
                    streak=excluded.streak,
                    last_correct=excluded.last_correct,
                    last_confidence=excluded.last_confidence,
                    updated_at=excluded.updated_at
                """,
                (
                    question.course_id,
                    question.id,
                    next_review.due_on.isoformat(),
                    next_review.interval_days,
                    next_review.streak,
                    int(correct),
                    confidence,
                    now,
                ),
            )
        schedule = ReviewSchedule(
            course_id=question.course_id,
            question_id=question.id,
            due_on=next_review.due_on.isoformat(),
            interval_days=next_review.interval_days,
            streak=next_review.streak,
            last_correct=correct,
            last_confidence=confidence,
        )
        return int(cursor.lastrowid), schedule

    def due_schedules(self, on_date: date | None = None) -> tuple[ReviewSchedule, ...]:
        due_on = (on_date or date.today()).isoformat()
        return tuple(
            ReviewSchedule(
                course_id=str(row["course_id"]),
                question_id=str(row["question_id"]),
                due_on=str(row["due_on"]),
                interval_days=int(row["interval_days"]),
                streak=int(row["streak"]),
                last_correct=bool(row["last_correct"]),
                last_confidence=int(row["last_confidence"]),
            )
            for row in self.connection.execute(
                """
                SELECT * FROM review_schedule
                WHERE due_on <= ?
                ORDER BY due_on, last_correct, last_confidence
                """,
                (due_on,),
            )
        )

    def start_practice(
        self,
        course_id: str,
        mode: str,
        questions: Sequence[QuizQuestion],
    ) -> int:
        if not questions:
            raise ValueError("연습을 시작하려면 문항이 필요하다")
        now = utc_now()
        with self.connection:
            cursor = self.connection.execute(
                """
                INSERT INTO practice_sessions(
                    course_id, mode, started_at, target_question_count, status
                ) VALUES (?, ?, ?, ?, 'active')
                """,
                (course_id, mode, now, len(questions)),
            )
            session_id = int(cursor.lastrowid)
            self.connection.executemany(
                """
                INSERT INTO practice_session_questions(
                    session_id, position, course_id, question_id
                ) VALUES (?, ?, ?, ?)
                """,
                [
                    (session_id, position, question.course_id, question.id)
                    for position, question in enumerate(questions)
                ],
            )
        return session_id

    def attach_attempt(self, session_id: int, position: int, attempt_id: int, correct: bool) -> None:
        with self.connection:
            cursor = self.connection.execute(
                """
                UPDATE practice_session_questions
                SET attempt_id=? WHERE session_id=? AND position=? AND attempt_id IS NULL
                """,
                (attempt_id, session_id, position),
            )
            if cursor.rowcount:
                self.connection.execute(
                    """
                    UPDATE practice_sessions
                    SET answered_count=answered_count + 1,
                        correct_count=correct_count + ?
                    WHERE id=? AND status='active'
                    """,
                    (int(correct), session_id),
                )

    def complete_practice(self, session_id: int) -> None:
        row = self.connection.execute(
            "SELECT started_at FROM practice_sessions WHERE id=?", (session_id,)
        ).fetchone()
        if row is None:
            return
        from datetime import datetime, timezone

        ended = datetime.now(timezone.utc)
        started = datetime.fromisoformat(str(row["started_at"]))
        duration = max(0.0, (ended - started).total_seconds())
        with self.connection:
            self.connection.execute(
                """
                UPDATE practice_sessions
                SET ended_at=?, duration_seconds=?, status='completed'
                WHERE id=? AND status='active'
                """,
                (ended.isoformat(timespec="seconds"), duration, session_id),
            )

    def topic_insights(self) -> tuple[TopicInsight, ...]:
        return tuple(
            TopicInsight(
                course_id=str(row["course_id"]),
                skill_id=str(row["skill_id"]),
                topic=str(row["topic"]),
                attempts=int(row["attempts"]),
                accuracy=float(row["accuracy"] or 0),
                average_confidence=float(row["average_confidence"] or 0),
                average_response_seconds=float(row["average_response_seconds"] or 0),
            )
            for row in self.connection.execute(
                """
                SELECT course_id, skill_id, topic, COUNT(*) AS attempts,
                       AVG(is_correct) AS accuracy,
                       AVG(confidence) AS average_confidence,
                       AVG(response_time_seconds) AS average_response_seconds
                FROM quiz_attempts
                GROUP BY course_id, skill_id, topic
                ORDER BY accuracy, attempts DESC, topic
                """
            )
        )

    def weakness_by_course(self) -> dict[str, float]:
        grouped: dict[str, list[float]] = defaultdict(list)
        for insight in self.topic_insights():
            grouped[insight.course_id].append(insight.weakness)
        return {
            course_id: sum(values) / len(values)
            for course_id, values in grouped.items()
            if values
        }

    def skill_mastery(self) -> tuple[SkillMastery, ...]:
        evidence: dict[str, SkillEvidence] = {}
        skill_ids = [str(row["skill_id"]) for row in self.connection.execute("SELECT skill_id FROM skills")]
        for skill_id in skill_ids:
            attempt = self.connection.execute(
                """
                SELECT COUNT(*) AS total, COALESCE(SUM(is_correct), 0) AS correct,
                       COALESCE(SUM(confidence), 0) AS confidence
                FROM quiz_attempts WHERE skill_id=?
                """,
                (skill_id,),
            ).fetchone()
            lessons = self.connection.execute(
                """
                SELECT COUNT(*) AS total,
                       COALESCE(SUM(CASE WHEN lp.status='completed' THEN 1 ELSE 0 END), 0) AS completed
                FROM lesson_skills ls
                LEFT JOIN lesson_progress lp
                  ON lp.course_id=ls.course_id AND lp.lesson_id=ls.lesson_id
                WHERE ls.skill_id=?
                """,
                (skill_id,),
            ).fetchone()
            review = self.connection.execute(
                """
                SELECT COALESCE(MAX(rs.streak), 0) AS streak
                FROM review_schedule rs
                JOIN quiz_questions q
                  ON q.course_id=rs.course_id AND q.question_id=rs.question_id
                WHERE q.skill_id=?
                """,
                (skill_id,),
            ).fetchone()
            evidence[skill_id] = SkillEvidence(
                skill_id=skill_id,
                correct_attempts=int(attempt["correct"]),
                total_attempts=int(attempt["total"]),
                confidence_total=int(attempt["confidence"]),
                completed_lessons=int(lessons["completed"]),
                total_lessons=int(lessons["total"]),
                review_streak=int(review["streak"]),
            )
        return calculate_all_mastery(evidence.values())

    def save_note(
        self,
        *,
        title: str,
        body_markdown: str,
        course_id: str | None = None,
        lesson_id: str | None = None,
        source_url: str | None = None,
        note_id: int | None = None,
    ) -> int:
        if not title.strip():
            raise ValueError("Note 제목이 필요하다")
        now = utc_now()
        with self.connection:
            if note_id is None:
                cursor = self.connection.execute(
                    """
                    INSERT INTO notes(
                        course_id, lesson_id, title, body_markdown, source_url,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (course_id, lesson_id, title.strip(), body_markdown, source_url, now, now),
                )
                return int(cursor.lastrowid)
            self.connection.execute(
                """
                UPDATE notes SET title=?, body_markdown=?, source_url=?, updated_at=?
                WHERE id=?
                """,
                (title.strip(), body_markdown, source_url, now, note_id),
            )
        return note_id

    def delete_note(self, note_id: int) -> None:
        with self.connection:
            self.connection.execute("DELETE FROM notes WHERE id=?", (note_id,))

    def notes(
        self,
        query: str = "",
        *,
        course_id: str | None = None,
        lesson_id: str | None = None,
    ) -> tuple[Note, ...]:
        clauses = ["1=1"]
        parameters: list[object] = []
        if query.strip():
            clauses.append("(title LIKE ? OR body_markdown LIKE ? OR source_url LIKE ?)")
            pattern = f"%{query.strip()}%"
            parameters.extend([pattern, pattern, pattern])
        if course_id:
            clauses.append("course_id=?")
            parameters.append(course_id)
        if lesson_id:
            clauses.append("lesson_id=?")
            parameters.append(lesson_id)
        return tuple(
            Note(
                id=int(row["id"]),
                title=str(row["title"]),
                body_markdown=str(row["body_markdown"]),
                course_id=row["course_id"],
                lesson_id=row["lesson_id"],
                source_url=row["source_url"],
                created_at=str(row["created_at"]),
                updated_at=str(row["updated_at"]),
            )
            for row in self.connection.execute(
                f"SELECT * FROM notes WHERE {' AND '.join(clauses)} ORDER BY updated_at DESC, id DESC",
                parameters,
            )
        )

    def get_setting(self, key: str, default: object = None) -> object:
        row = self.connection.execute("SELECT value_json FROM settings WHERE key=?", (key,)).fetchone()
        return json.loads(str(row["value_json"])) if row else default

    def set_setting(self, key: str, value: object) -> None:
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO settings(key, value_json, updated_at) VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value_json=excluded.value_json,
                    updated_at=excluded.updated_at
                """,
                (key, json.dumps(value, ensure_ascii=False), utc_now()),
            )

    def study_summary(self) -> StudySummary:
        sessions = self.connection.execute(
            """
            SELECT COUNT(*) AS sessions, COALESCE(SUM(duration_minutes), 0) AS minutes,
                   COUNT(DISTINCT substr(started_at, 1, 10)) AS active_days
            FROM study_sessions WHERE status='completed'
            """
        ).fetchone()
        attempts = self.connection.execute(
            "SELECT COUNT(*) AS attempts, COALESCE(AVG(is_correct), 0) AS accuracy FROM quiz_attempts"
        ).fetchone()
        return StudySummary(
            completed_sessions=int(sessions["sessions"]),
            completed_minutes=float(sessions["minutes"]),
            active_days=int(sessions["active_days"]),
            answered_questions=int(attempts["attempts"]),
            accuracy=float(attempts["accuracy"]),
        )

    def study_activity(
        self,
        start_on: date,
        end_on: date,
        *,
        local_timezone: tzinfo | None = None,
    ) -> tuple[StudyActivity, ...]:
        """Return completed lessons and answered questions in a local date range."""
        if end_on < start_on:
            raise ValueError("end_on must be on or after start_on")
        resolved_timezone = local_timezone or datetime.now().astimezone().tzinfo
        if resolved_timezone is None:  # pragma: no cover - platform fallback
            resolved_timezone = timezone.utc

        start_local = datetime.combine(start_on, time.min, tzinfo=resolved_timezone)
        end_local = datetime.combine(
            end_on + timedelta(days=1),
            time.min,
            tzinfo=resolved_timezone,
        )
        start_utc = start_local.astimezone(timezone.utc).isoformat(timespec="seconds")
        end_utc = end_local.astimezone(timezone.utc).isoformat(timespec="seconds")

        lesson_rows = self.connection.execute(
            """
            SELECT course_id, lesson_id, completed_at
            FROM lesson_progress
            WHERE status='completed'
              AND completed_at >= ?
              AND completed_at < ?
            ORDER BY completed_at, course_id, lesson_id
            """,
            (start_utc, end_utc),
        ).fetchall()
        session_rows = self.connection.execute(
            """
            SELECT course_id, lesson_id, ended_at, duration_minutes
            FROM study_sessions
            WHERE status='completed'
              AND ended_at >= ?
              AND ended_at < ?
            """,
            (start_utc, end_utc),
        ).fetchall()

        session_minutes: dict[tuple[str, str, date], float] = defaultdict(float)
        for row in session_rows:
            occurred_at = _local_datetime(str(row["ended_at"]), resolved_timezone)
            key = (str(row["course_id"]), str(row["lesson_id"]), occurred_at.date())
            session_minutes[key] += float(row["duration_minutes"] or 0)

        activities: list[StudyActivity] = []
        for row in lesson_rows:
            course_id = str(row["course_id"])
            lesson_id = str(row["lesson_id"])
            occurred_at = _local_datetime(str(row["completed_at"]), resolved_timezone)
            activities.append(
                StudyActivity(
                    kind="lesson",
                    course_id=course_id,
                    lesson_id=lesson_id,
                    occurred_at=occurred_at,
                    duration_minutes=session_minutes.get(
                        (course_id, lesson_id, occurred_at.date()),
                        0.0,
                    ),
                )
            )

        for row in self.connection.execute(
            """
            SELECT course_id, topic, is_correct, response_time_seconds, attempted_at
            FROM quiz_attempts
            WHERE attempted_at >= ?
              AND attempted_at < ?
            ORDER BY attempted_at, id
            """,
            (start_utc, end_utc),
        ):
            activities.append(
                StudyActivity(
                    kind="quiz",
                    course_id=str(row["course_id"]),
                    topic=str(row["topic"]),
                    correct=bool(row["is_correct"]),
                    occurred_at=_local_datetime(
                        str(row["attempted_at"]), resolved_timezone
                    ),
                    duration_minutes=float(row["response_time_seconds"]) / 60,
                )
            )

        return tuple(sorted(activities, key=lambda item: item.occurred_at))


def _local_datetime(value: str, local_timezone: tzinfo) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(local_timezone)
