from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class SkillEvidence:
    skill_id: str
    correct_attempts: int = 0
    total_attempts: int = 0
    confidence_total: int = 0
    completed_lessons: int = 0
    total_lessons: int = 0
    review_streak: int = 0


@dataclass(frozen=True)
class SkillMastery:
    skill_id: str
    score: int
    quiz_score: float
    confidence_score: float
    completion_score: float
    review_score: float
    explanation: str


def calculate_mastery(evidence: SkillEvidence) -> SkillMastery:
    quiz = evidence.correct_attempts / evidence.total_attempts if evidence.total_attempts else 0.0
    confidence = (
        evidence.confidence_total / (evidence.total_attempts * 5)
        if evidence.total_attempts
        else 0.0
    )
    completion = (
        evidence.completed_lessons / evidence.total_lessons
        if evidence.total_lessons
        else 0.0
    )
    review = min(max(evidence.review_streak, 0) / 3, 1.0)
    score = round((quiz * 0.50 + confidence * 0.15 + completion * 0.25 + review * 0.10) * 100)
    explanation = (
        f"정확도 {quiz:.0%}×50% + 자신감 {confidence:.0%}×15% + "
        f"Lesson 완료 {completion:.0%}×25% + 복습 연속성 {review:.0%}×10%"
    )
    return SkillMastery(
        skill_id=evidence.skill_id,
        score=score,
        quiz_score=quiz,
        confidence_score=confidence,
        completion_score=completion,
        review_score=review,
        explanation=explanation,
    )


def calculate_all_mastery(evidence: Iterable[SkillEvidence]) -> tuple[SkillMastery, ...]:
    return tuple(
        sorted(
            (calculate_mastery(item) for item in evidence),
            key=lambda item: (-item.score, item.skill_id),
        )
    )
