from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Mapping, Sequence

from learning_os.core.models import Course, StudyRecommendation


@dataclass(frozen=True)
class ScheduleFactors:
    course_id: str
    score: float
    urgency: float
    incompletion: float
    weakness: float


def rank_courses(
    courses: Sequence[Course],
    progress: Mapping[tuple[str, str], str],
    weakness_by_course: Mapping[str, float] | None = None,
    *,
    today: date | None = None,
) -> tuple[tuple[Course, ScheduleFactors], ...]:
    current = today or date.today()
    weakness_by_course = weakness_by_course or {}
    ranked: list[tuple[Course, ScheduleFactors]] = []
    for course in courses:
        if course.status != "active":
            continue
        total = len(course.required_lessons)
        completed = sum(
            1
            for lesson in course.required_lessons
            if progress.get((course.id, lesson.id)) == "completed"
        )
        incompletion = 1 - (completed / total if total else 1)
        if course.schedule.target_date:
            days = max(0, (course.schedule.target_date - current).days)
            urgency = 1 / max(1, days + 1)
        else:
            urgency = 0.0
        weakness = max(0.0, min(1.0, float(weakness_by_course.get(course.id, 0.0))))
        score = course.schedule.priority + urgency * 100 + incompletion * 20 + weakness * 30
        ranked.append(
            (
                course,
                ScheduleFactors(
                    course_id=course.id,
                    score=score,
                    urgency=urgency,
                    incompletion=incompletion,
                    weakness=weakness,
                ),
            )
        )
    return tuple(sorted(ranked, key=lambda item: (-item[1].score, item[0].title.casefold())))


def build_curriculum_plan(
    courses: Sequence[Course],
    progress: Mapping[tuple[str, str], str],
    available_minutes: int = 60,
    max_lessons: int = 3,
    weakness_by_course: Mapping[str, float] | None = None,
    allowed_languages: set[str] | None = None,
    *,
    today: date | None = None,
) -> tuple[StudyRecommendation, ...]:
    candidates: list[StudyRecommendation] = []
    for course, factors in rank_courses(
        courses,
        progress,
        weakness_by_course,
        today=today,
    ):
        lesson = next(
            (
                item
                for item in course.required_lessons
                if progress.get((course.id, item.id)) != "completed"
                and (
                    allowed_languages is None
                    or item.language is None
                    or item.language in allowed_languages
                )
            ),
            None,
        )
        if lesson is None:
            continue
        reasons = []
        if course.schedule.target_date:
            reasons.append(f"{course.schedule.target_date.isoformat()} 목표")
        if factors.weakness >= 0.4:
            reasons.append("취약 영역 보강")
        reasons.append("다음 미완료 Lesson")
        candidates.append(
            StudyRecommendation(course=course, lesson=lesson, reason=" · ".join(reasons))
        )

    chosen: list[StudyRecommendation] = []
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
