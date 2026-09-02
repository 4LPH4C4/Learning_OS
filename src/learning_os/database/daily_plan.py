from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DailyStudyPlanItem:
    course_id: str
    lesson_id: str


@dataclass(frozen=True)
class DailyStudyPlan:
    local_date: str
    available_minutes: int
    items: tuple[DailyStudyPlanItem, ...]
