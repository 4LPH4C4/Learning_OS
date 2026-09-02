from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Iterable, Mapping

from learning_os.core.assessment import QuizQuestion
from learning_os.core.adaptive import MockExamSet
from learning_os.core.models import Course


@dataclass(frozen=True)
class PracticeProfile:
    question_count: int
    duration_minutes: int | None = None
    target_score: int = 80


def profile_for(course: Course, mode: str) -> PracticeProfile:
    settings = course.quiz_settings or {}
    raw = settings.get("mock_exam", {}) if mode == "mock_exam" else settings
    if not isinstance(raw, dict):
        raw = {}
    default_count = 10 if mode == "mock_exam" else 5
    return PracticeProfile(
        question_count=max(1, int(raw.get("question_count", default_count))),
        duration_minutes=(
            max(1, int(raw["duration_minutes"]))
            if raw.get("duration_minutes") is not None
            else None
        ),
        target_score=max(0, min(100, int(raw.get("target_score", 80)))),
    )


def profile_for_set(exam_set: MockExamSet) -> PracticeProfile:
    return PracticeProfile(
        question_count=exam_set.question_count,
        duration_minutes=exam_set.duration_minutes,
        target_score=exam_set.target_score,
    )


def select_questions(
    questions: Iterable[QuizQuestion],
    *,
    count: int,
    seed: str,
    weakness_by_topic: Mapping[str, float] | None = None,
) -> tuple[QuizQuestion, ...]:
    weakness_by_topic = weakness_by_topic or {}

    def ranking(question: QuizQuestion) -> tuple[float, str]:
        weakness = float(weakness_by_topic.get(question.topic, 0.0))
        digest = hashlib.sha256(f"{seed}:{question.course_id}:{question.id}".encode()).hexdigest()
        return (-weakness, digest)

    available = sorted(tuple(questions), key=ranking)
    return tuple(available[: max(0, count)])


def score_percent(correct: int, total: int) -> int:
    return round(correct / total * 100) if total else 0
