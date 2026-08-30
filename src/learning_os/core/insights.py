from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TopicInsight:
    course_id: str
    skill_id: str
    topic: str
    attempts: int
    accuracy: float
    average_confidence: float
    average_response_seconds: float

    @property
    def weakness(self) -> float:
        confidence_gap = max(0.0, 1 - self.average_confidence / 5)
        return min(1.0, (1 - self.accuracy) * 0.75 + confidence_gap * 0.25)


@dataclass(frozen=True)
class Note:
    id: int
    title: str
    body_markdown: str
    course_id: str | None
    lesson_id: str | None
    source_url: str | None
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class StudySummary:
    completed_sessions: int
    completed_minutes: float
    active_days: int
    answered_questions: int
    accuracy: float
