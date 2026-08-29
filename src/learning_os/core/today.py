from __future__ import annotations

from datetime import date
from typing import Mapping, Sequence

from learning_os.core.models import Course, StudyRecommendation


def build_today_plan(
    courses: Sequence[Course],
    progress: Mapping[tuple[str, str], str],
    available_minutes: int = 60,
    max_lessons: int = 3,
) -> tuple[StudyRecommendation, ...]:
    active = sorted(
        (course for course in courses if course.status == "active"),
        key=lambda course: (
            -course.schedule.priority,
            course.schedule.target_date or date.max,
            course.title.casefold(),
        ),
    )
    candidates = []
    for course in active:
        lesson = next(
            (
                item
                for item in course.required_lessons
                if progress.get((course.id, item.id)) != "completed"
            ),
            None,
        )
        if lesson:
            target = course.schedule.target_date
            reason = "우선순위가 높은 다음 미완료 Lesson"
            if target:
                reason = f"{target.isoformat()} 목표 · 다음 미완료 Lesson"
            candidates.append(StudyRecommendation(course=course, lesson=lesson, reason=reason))

    chosen = []
    used = 0
    for candidate in candidates:
        if len(chosen) >= max_lessons:
            break
        duration = candidate.lesson.duration_minutes
        if used + duration <= available_minutes:
            chosen.append(candidate)
            used += duration
    if not chosen and candidates:
        chosen.append(min(candidates, key=lambda item: item.lesson.duration_minutes))
    return tuple(chosen)
