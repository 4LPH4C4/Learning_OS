from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from learning_os.core.assessment import evaluate_answer
from learning_os.core.manifests import load_manifest
from learning_os.core.question_bank import QuestionBankError, load_question_file
from learning_os.core.practice import profile_for
from learning_os.core.review import schedule_review
from learning_os.core.scheduler import build_curriculum_plan, rank_courses
from learning_os.database.connection import connect
from learning_os.database.learning_repository import LearningRepository
from learning_os.database.migrations import apply_migrations
from learning_os.database.progress_repository import ProgressRepository


ROOT = Path(__file__).parents[1]
QUESTION_BANK = """\
schema_version: 1
course_id: aice-associate
questions:
  - id: dataframe-shape
    lesson_id: pandas-first-steps
    skill_id: pandas
    topic: DataFrame inspection
    difficulty: 2
    type: single_choice
    prompt: 행과 열의 개수를 함께 확인하는 속성은?
    options:
      - {id: a, text: df.shape}
      - {id: b, text: df.head()}
    correct_answers: [a]
    explanation: shape는 (행, 열) tuple을 반환한다.
    incorrect_explanations:
      b: head는 일부 행을 보여주지만 전체 크기를 반환하지 않는다.
  - id: missing-count
    lesson_id: data-cleaning-checklist
    skill_id: data-analysis
    topic: Missing values
    difficulty: 3
    type: short_answer
    prompt: 결측값 개수를 세는 핵심 메서드 이름은?
    options: []
    correct_answers: [isna, isnull]
    explanation: isna 또는 isnull로 결측 여부를 확인한다.
"""


def load_questions(tmp_path: Path):
    course = load_manifest(ROOT / "courses" / "aice-associate" / "course.yaml")
    path = tmp_path / "questions.yaml"
    path.write_text(QUESTION_BANK, encoding="utf-8")
    return course, load_question_file(course, path)


def repository(tmp_path: Path) -> tuple[LearningRepository, ProgressRepository]:
    connection = connect(tmp_path / "learning.db")
    apply_migrations(connection, ROOT / "migrations")
    return LearningRepository(connection), ProgressRepository(connection)


def test_phase2_migration_preserves_phase1_progress(tmp_path: Path) -> None:
    migration_dir = tmp_path / "migrations"
    migration_dir.mkdir()
    (migration_dir / "001_initial.sql").write_text(
        (ROOT / "migrations" / "001_initial.sql").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    connection = connect(tmp_path / "upgrade.db")
    apply_migrations(connection, migration_dir)
    ProgressRepository(connection).mark_completed("legacy-course", "legacy-lesson")
    (migration_dir / "002_phase2_learning.sql").write_text(
        (ROOT / "migrations" / "002_phase2_learning.sql").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    apply_migrations(connection, migration_dir)

    assert ProgressRepository(connection).statuses() == {
        ("legacy-course", "legacy-lesson"): "completed"
    }
    assert connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='quiz_attempts'"
    ).fetchone()


def test_question_bank_and_answer_evaluation(tmp_path: Path) -> None:
    _, questions = load_questions(tmp_path)

    correct = evaluate_answer(questions[0], ["a"])
    wrong = evaluate_answer(questions[0], ["b"])
    short = evaluate_answer(questions[1], [" ISNULL "])

    assert correct.correct
    assert not wrong.correct and "전체 크기" in wrong.feedback
    assert short.correct


def test_question_bank_rejects_unknown_correct_option(tmp_path: Path) -> None:
    course, _ = load_questions(tmp_path)
    path = tmp_path / "broken.yaml"
    path.write_text(QUESTION_BANK.replace("correct_answers: [a]", "correct_answers: [missing]"), encoding="utf-8")

    with pytest.raises(QuestionBankError, match="존재하지 않는 option"):
        load_question_file(course, path)


@pytest.mark.parametrize(
    ("correct", "confidence", "streak", "days", "next_streak"),
    [
        (False, 5, 3, 1, 0),
        (True, 2, 0, 2, 1),
        (True, 4, 0, 4, 1),
        (True, 4, 1, 7, 2),
        (True, 4, 2, 14, 3),
        (True, 4, 3, 30, 4),
    ],
)
def test_spaced_repetition_rules(
    correct: bool,
    confidence: int,
    streak: int,
    days: int,
    next_streak: int,
) -> None:
    result = schedule_review(
        correct=correct,
        confidence=confidence,
        previous_streak=streak,
        today=date(2026, 8, 30),
    )

    assert result.interval_days == days
    assert result.streak == next_streak


def test_attempt_persists_review_and_practice_idempotently(tmp_path: Path) -> None:
    course, questions = load_questions(tmp_path)
    learning, _ = repository(tmp_path)
    learning.sync_catalog([course], questions)
    session_id = learning.start_practice(course.id, "quiz", questions)

    attempt_id, schedule = learning.record_attempt(
        questions[0],
        ["b"],
        correct=False,
        response_time_seconds=8.5,
        confidence=4,
        today=date(2026, 8, 30),
    )
    learning.attach_attempt(session_id, 0, attempt_id, False)
    learning.attach_attempt(session_id, 0, attempt_id, False)

    row = learning.connection.execute("SELECT * FROM practice_sessions WHERE id=?", (session_id,)).fetchone()
    assert schedule.due_on == "2026-08-31"
    assert len(learning.due_schedules(date(2026, 8, 31))) == 1
    assert row["answered_count"] == 1 and row["correct_count"] == 0


def test_notes_settings_insights_and_mastery(tmp_path: Path) -> None:
    course, questions = load_questions(tmp_path)
    learning, progress = repository(tmp_path)
    learning.sync_catalog([course], questions)
    progress.mark_completed(course.id, "pandas-first-steps")
    learning.record_attempt(
        questions[0],
        ["a"],
        correct=True,
        response_time_seconds=4,
        confidence=5,
        today=date(2026, 8, 30),
    )
    note_id = learning.save_note(
        title="shape 정리",
        body_markdown="행과 열을 함께 본다.",
        course_id=course.id,
        lesson_id="pandas-first-steps",
    )
    learning.set_setting("default_study_minutes", 45)

    assert learning.notes("행과 열")[0].id == note_id
    assert learning.get_setting("default_study_minutes") == 45
    assert learning.topic_insights()[0].accuracy == 1.0
    pandas = next(item for item in learning.skill_mastery() if item.skill_id == "pandas")
    assert pandas.score > 0 and "정확도" in pandas.explanation


def test_scheduler_uses_weakness_without_breaking_time_budget() -> None:
    aice = load_manifest(ROOT / "courses" / "aice-associate" / "course.yaml")
    pspo = load_manifest(ROOT / "courses" / "pspo-i" / "course.yaml")
    aice = replace(aice, schedule=replace(aice.schedule, priority=100, target_date=None))
    pspo = replace(pspo, schedule=replace(pspo.schedule, priority=100, target_date=None))

    ranked = rank_courses(
        [pspo, aice],
        {},
        {aice.id: 1.0, pspo.id: 0.0},
        today=date(2026, 8, 30),
    )
    plan = build_curriculum_plan(
        [pspo, aice],
        {},
        available_minutes=25,
        weakness_by_course={aice.id: 1.0},
        today=date(2026, 8, 30),
    )

    assert ranked[0][0].id == aice.id
    assert len(plan) == 1 and plan[0].lesson.duration_minutes <= 25


def test_scheduler_respects_content_language_setting() -> None:
    aice = load_manifest(ROOT / "courses" / "aice-associate" / "course.yaml")
    ai_course = load_manifest(ROOT / "courses" / "ai-for-beginners" / "course.yaml")

    english_only = build_curriculum_plan(
        [aice, ai_course],
        {},
        available_minutes=60,
        allowed_languages={"en"},
        today=date(2026, 8, 30),
    )

    assert [item.course.id for item in english_only] == ["ai-for-beginners"]


def test_mock_exam_profiles_are_manifest_driven() -> None:
    pspo = load_manifest(ROOT / "courses" / "pspo-i" / "course.yaml")
    sqld = load_manifest(ROOT / "courses" / "sqld" / "course.yaml")

    assert profile_for(pspo, "mock_exam").question_count == 80
    assert profile_for(pspo, "mock_exam").duration_minutes == 60
    assert profile_for(pspo, "mock_exam").target_score == 90
    assert profile_for(sqld, "mock_exam").question_count == 50
