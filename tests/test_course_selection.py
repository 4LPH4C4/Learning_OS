from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from learning_os.config import load_settings
from learning_os.core.catalog import discover_courses
from learning_os.core.course_selection import (
    normalize_selected_course_ids,
    selectable_courses,
    selected_courses,
)


ROOT = Path(__file__).parents[1]


def test_course_selection_filters_stale_and_disabled_ids_in_catalog_order() -> None:
    catalog = discover_courses(load_settings(ROOT).courses_dir)
    disabled_id = catalog.courses[0].id
    courses = (replace(catalog.courses[0], status="disabled"), *catalog.courses[1:])
    requested = ["ncs-core", "missing-course", "pspo-i", disabled_id]

    normalized = normalize_selected_course_ids(courses, requested)

    assert normalized == tuple(
        course.id
        for course in courses
        if course.status != "disabled" and course.id in requested
    )
    assert disabled_id not in normalized
    assert selected_courses(courses, normalized) == tuple(
        course for course in courses if course.id in normalized
    )
    assert disabled_id not in {course.id for course in selectable_courses(courses)}


def test_course_selection_uses_empty_safe_default_for_invalid_setting() -> None:
    courses = discover_courses(load_settings(ROOT).courses_dir).courses

    assert normalize_selected_course_ids(courses, None) == ()
    assert normalize_selected_course_ids(courses, "pspo-i") == ()
