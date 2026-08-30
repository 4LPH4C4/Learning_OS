from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence


QuestionType = Literal["single_choice", "multiple_choice", "short_answer"]


@dataclass(frozen=True)
class QuizOption:
    id: str
    text: str


@dataclass(frozen=True)
class QuizQuestion:
    id: str
    course_id: str
    lesson_id: str | None
    skill_id: str
    topic: str
    difficulty: int
    type: QuestionType
    prompt: str
    options: tuple[QuizOption, ...]
    correct_answers: tuple[str, ...]
    explanation: str
    incorrect_explanations: tuple[tuple[str, str], ...] = ()
    source_ref: str | None = None
    content_hash: str = ""

    def option_text(self, option_id: str) -> str:
        option = next((item for item in self.options if item.id == option_id), None)
        return option.text if option else option_id

    def incorrect_reason(self, option_id: str) -> str | None:
        return dict(self.incorrect_explanations).get(option_id)


@dataclass(frozen=True)
class AnswerResult:
    correct: bool
    normalized_answers: tuple[str, ...]
    feedback: str


@dataclass(frozen=True)
class ReviewSchedule:
    course_id: str
    question_id: str
    due_on: str
    interval_days: int
    streak: int
    last_correct: bool
    last_confidence: int


@dataclass(frozen=True)
class ReviewQuestion:
    question: QuizQuestion
    schedule: ReviewSchedule


def _normalize_text(value: str) -> str:
    return " ".join(value.casefold().strip().split())


def evaluate_answer(question: QuizQuestion, answers: Sequence[str]) -> AnswerResult:
    submitted = tuple(str(answer).strip() for answer in answers if str(answer).strip())
    if question.type == "short_answer":
        normalized = tuple(_normalize_text(answer) for answer in submitted)
        accepted = {_normalize_text(answer) for answer in question.correct_answers}
        correct = len(normalized) == 1 and normalized[0] in accepted
    else:
        normalized = tuple(sorted(set(submitted)))
        correct = normalized == tuple(sorted(set(question.correct_answers)))

    feedback = question.explanation
    if not correct and len(submitted) == 1:
        feedback = question.incorrect_reason(submitted[0]) or feedback
    return AnswerResult(correct=correct, normalized_answers=normalized, feedback=feedback)
