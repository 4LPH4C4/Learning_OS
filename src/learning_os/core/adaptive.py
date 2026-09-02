from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Mapping

from learning_os.core.models import Course, Lesson


@dataclass(frozen=True)
class PlacementBand:
    id: str
    label: str
    min_score: int


@dataclass(frozen=True)
class PlacementConfig:
    lesson_id: str
    question_set: str
    question_count: int
    duration_minutes: int
    levels: tuple[PlacementBand, ...]
    level_pass_score: int
    cumulative_pass_score: int


@dataclass(frozen=True)
class PlacementResult:
    course_id: str
    level_id: str
    level_label: str
    score_percent: int
    correct_count: int
    question_count: int
    completed_at: str
    level_scores: tuple[tuple[str, int, int], ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "course_id": self.course_id,
            "level_id": self.level_id,
            "level_label": self.level_label,
            "score_percent": self.score_percent,
            "correct_count": self.correct_count,
            "question_count": self.question_count,
            "completed_at": self.completed_at,
            "level_scores": [
                {"level_id": level_id, "correct": correct, "total": total}
                for level_id, correct, total in self.level_scores
            ],
        }


@dataclass(frozen=True)
class MockExamSet:
    id: str
    title: str
    question_count: int
    duration_minutes: int
    target_score: int


def placement_setting_key(course_id: str) -> str:
    return f"placement-result:{course_id}"


def placement_config(course: Course) -> PlacementConfig | None:
    settings = course.quiz_settings or {}
    raw = settings.get("placement")
    if not isinstance(raw, dict):
        return None
    levels_raw = raw.get("levels")
    if not isinstance(levels_raw, list) or not levels_raw:
        raise ValueError(f"{course.id}: placement.levels가 필요하다")
    levels: list[PlacementBand] = []
    for item in levels_raw:
        if not isinstance(item, dict):
            raise ValueError(f"{course.id}: placement.levels 항목은 mapping이어야 한다")
        level_id = str(item.get("id", "")).strip()
        label = str(item.get("label", level_id)).strip()
        if not level_id or not label:
            raise ValueError(f"{course.id}: placement level id와 label이 필요하다")
        levels.append(
            PlacementBand(
                id=level_id,
                label=label,
                min_score=max(0, min(100, int(item.get("min_score", 0)))),
            )
        )
    if len({item.id for item in levels}) != len(levels):
        raise ValueError(f"{course.id}: placement level id가 중복됐다")
    if [item.min_score for item in levels] != sorted(item.min_score for item in levels):
        raise ValueError(f"{course.id}: placement level은 min_score 오름차순이어야 한다")
    configured_levels = {item.id for item in levels}
    unknown_levels = {
        lesson.level
        for lesson in course.lessons
        if lesson.level is not None and lesson.level not in configured_levels
    }
    if unknown_levels:
        raise ValueError(
            f"{course.id}: placement.levels에 없는 Lesson level이 있다: "
            f"{', '.join(sorted(unknown_levels))}"
        )
    lesson_id = str(raw.get("lesson_id", "")).strip()
    if not lesson_id or not any(lesson.id == lesson_id for lesson in course.lessons):
        raise ValueError(f"{course.id}: placement.lesson_id가 Course Lesson과 맞지 않는다")
    question_set = str(raw.get("question_set", "placement")).strip()
    if not question_set:
        raise ValueError(f"{course.id}: placement.question_set이 필요하다")
    return PlacementConfig(
        lesson_id=lesson_id,
        question_set=question_set,
        question_count=max(1, int(raw.get("question_count", 20))),
        duration_minutes=max(1, int(raw.get("duration_minutes", 30))),
        levels=tuple(levels),
        level_pass_score=max(0, min(100, int(raw.get("level_pass_score", 60)))),
        cumulative_pass_score=max(
            0,
            min(100, int(raw.get("cumulative_pass_score", 65))),
        ),
    )


def placement_result(value: object, course: Course) -> PlacementResult | None:
    config = placement_config(course)
    if config is None or not isinstance(value, Mapping):
        return None
    selected_level_id = str(value.get("level_id", ""))
    band = next((item for item in config.levels if item.id == selected_level_id), None)
    if band is None:
        return None
    try:
        raw_level_scores = value.get("level_scores", [])
        scores: list[tuple[str, int, int]] = []
        if isinstance(raw_level_scores, list):
            valid_levels = {item.id for item in config.levels}
            for item in raw_level_scores:
                if not isinstance(item, Mapping):
                    continue
                score_level_id = str(item.get("level_id", ""))
                if score_level_id in valid_levels:
                    scores.append(
                        (
                            score_level_id,
                            max(0, int(item.get("correct", 0))),
                            max(0, int(item.get("total", 0))),
                        )
                    )
        return PlacementResult(
            course_id=course.id,
            level_id=selected_level_id,
            level_label=band.label,
            score_percent=max(0, min(100, int(value.get("score_percent", 0)))),
            correct_count=max(0, int(value.get("correct_count", 0))),
            question_count=max(0, int(value.get("question_count", 0))),
            completed_at=str(value.get("completed_at", "")),
            level_scores=tuple(scores),
        )
    except (TypeError, ValueError):
        return None


def recommend_placement(
    course: Course,
    *,
    score_percent: int,
    correct_count: int,
    question_count: int,
    correct_by_level: Mapping[str, int] | None = None,
    total_by_level: Mapping[str, int] | None = None,
) -> PlacementResult:
    config = placement_config(course)
    if config is None:
        raise ValueError(f"{course.id}: placement 설정이 없다")
    score = max(0, min(100, int(score_percent)))
    band = config.levels[0]
    level_scores: tuple[tuple[str, int, int], ...] = ()
    if correct_by_level is not None and total_by_level is not None:
        score_items = [
            (
                level.id,
                max(0, int(correct_by_level.get(level.id, 0))),
                max(0, int(total_by_level.get(level.id, 0))),
            )
            for level in config.levels
        ]
        cumulative_correct = 0
        cumulative_total = 0
        for index, (_, level_correct, level_total) in enumerate(score_items[:-1]):
            cumulative_correct += min(level_correct, level_total)
            cumulative_total += level_total
            if not level_total or not cumulative_total:
                break
            level_rate = round(level_correct / level_total * 100)
            cumulative_rate = round(cumulative_correct / cumulative_total * 100)
            if (
                level_rate >= config.level_pass_score
                and cumulative_rate >= config.cumulative_pass_score
            ):
                band = config.levels[index + 1]
            else:
                break
        level_scores = tuple(score_items)
    else:
        for candidate in config.levels:
            if score >= candidate.min_score:
                band = candidate
            else:
                break
    return PlacementResult(
        course_id=course.id,
        level_id=band.id,
        level_label=band.label,
        score_percent=score,
        correct_count=max(0, int(correct_count)),
        question_count=max(0, int(question_count)),
        completed_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        level_scores=level_scores,
    )


def eligible_lessons(course: Course, result: PlacementResult | None) -> tuple[Lesson, ...]:
    config = placement_config(course)
    if config is None:
        return course.lessons
    if result is None:
        return tuple(lesson for lesson in course.lessons if lesson.id == config.lesson_id)
    level_order = {item.id: index for index, item in enumerate(config.levels)}
    start_index = level_order[result.level_id]
    return tuple(
        lesson
        for lesson in course.lessons
        if lesson.id == config.lesson_id
        or lesson.level is None
        or level_order.get(lesson.level, start_index) >= start_index
    )


def personalize_course(course: Course, result: PlacementResult | None) -> Course:
    allowed_ids = {lesson.id for lesson in eligible_lessons(course, result)}
    modules = tuple(
        replace(module, lessons=tuple(lesson for lesson in module.lessons if lesson.id in allowed_ids))
        for module in course.modules
    )
    return replace(course, modules=tuple(module for module in modules if module.lessons))


def mock_exam_sets(course: Course) -> tuple[MockExamSet, ...]:
    settings = course.quiz_settings or {}
    raw_sets = settings.get("mock_exam_sets", [])
    if not isinstance(raw_sets, list):
        raise ValueError(f"{course.id}: mock_exam_sets는 list여야 한다")
    result: list[MockExamSet] = []
    for item in raw_sets:
        if not isinstance(item, dict):
            raise ValueError(f"{course.id}: mock_exam_sets 항목은 mapping이어야 한다")
        set_id = str(item.get("id", "")).strip()
        if not set_id:
            raise ValueError(f"{course.id}: mock exam set id가 필요하다")
        result.append(
            MockExamSet(
                id=set_id,
                title=str(item.get("title", set_id)),
                question_count=max(1, int(item.get("question_count", 50))),
                duration_minutes=max(1, int(item.get("duration_minutes", 60))),
                target_score=max(0, min(100, int(item.get("target_score", 60)))),
            )
        )
    if len({item.id for item in result}) != len(result):
        raise ValueError(f"{course.id}: mock exam set id가 중복됐다")
    return tuple(result)
