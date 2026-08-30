from __future__ import annotations

from typing import Mapping, Sequence

from learning_os.core.models import Course, StudyRecommendation
from learning_os.core.scheduler import build_curriculum_plan


def build_today_plan(
    courses: Sequence[Course],
    progress: Mapping[tuple[str, str], str],
    available_minutes: int = 60,
    max_lessons: int = 3,
) -> tuple[StudyRecommendation, ...]:
    return build_curriculum_plan(
        courses,
        progress,
        available_minutes=available_minutes,
        max_lessons=max_lessons,
    )
