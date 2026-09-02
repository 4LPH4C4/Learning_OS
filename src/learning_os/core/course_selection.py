from __future__ import annotations

from collections.abc import Iterable

from learning_os.core.models import Course


SELECTED_COURSE_IDS_SETTING = "selected_course_ids"


def selectable_courses(courses: Iterable[Course]) -> tuple[Course, ...]:
    """Return Courses that a learner can include in their learning flow."""
    return tuple(course for course in courses if course.status != "disabled")


def normalize_selected_course_ids(
    courses: Iterable[Course],
    value: object,
) -> tuple[str, ...]:
    """Keep valid selections in catalog order and discard stale settings."""
    if not isinstance(value, (list, tuple)):
        return ()
    requested = {str(course_id) for course_id in value}
    return tuple(
        course.id
        for course in selectable_courses(courses)
        if course.id in requested
    )


def selected_courses(
    courses: Iterable[Course],
    selected_course_ids: Iterable[str],
) -> tuple[Course, ...]:
    selected = set(selected_course_ids)
    return tuple(
        course
        for course in selectable_courses(courses)
        if course.id in selected
    )
