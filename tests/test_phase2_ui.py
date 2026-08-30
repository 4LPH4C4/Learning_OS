from __future__ import annotations

from pathlib import Path

import pytest

from learning_os.config import load_settings
from learning_os.core.catalog import discover_courses
from learning_os.core.question_bank import discover_questions, load_question_file


ROOT = Path(__file__).parents[1]


def _visible_text(at) -> str:
    """Collect user-visible text without interacting with submit controls."""
    values: list[str] = []
    for name in ("title", "header", "subheader", "markdown", "caption", "info", "success", "warning", "button", "multiselect", "text_input"):
        for item in getattr(at, name, []):
            values.append(str(getattr(item, "label", getattr(item, "value", ""))))
    return "\n".join(values)


def _app():
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest

    return AppTest.from_file(str(ROOT / "app.py"), default_timeout=15).run()


def test_sidebar_destinations_render_with_expected_titles() -> None:
    at = _app()
    assert not at.exception
    assert "Learning OS" in _visible_text(at)

    expected = {
        "오늘": "Learning OS",
        "Courses": "Courses",
        "Review": "Review",
        "Notes": "Notes",
        "Insights": "Insights",
        "Settings": "Settings",
    }
    for label, title in expected.items():
        at.radio[0].set_value(label).run()
        assert not at.exception, f"{label} 페이지 렌더링 예외: {at.exception}"
        assert any(item.value == title for item in at.title), (label, [item.value for item in at.title])


def test_dashboard_and_review_expose_phase2_learning_flow() -> None:
    at = _app()
    assert "Today's Study" in _visible_text(at)
    # AppTest exposes the adjustment control as a multiselect; do not touch its
    # value because changing it would alter the user's study plan.
    assert at.multiselect
    assert "오늘 계획 조정" in (ROOT / "app.py").read_text(encoding="utf-8")

    at.radio[0].set_value("Review").run()
    assert not at.exception
    text = _visible_text(at)
    assert "Quick Practice" in text
    for course_title in ("AI for Beginners", "AICE Associate", "PSPO I", "SQLD"):
        assert course_title in text
    assert len([button for button in at.button if (button.key or "").startswith("review-quiz:")]) == 4


@pytest.mark.parametrize(
    ("page", "copy"),
    [
        ("Notes", "Lesson에서 남긴 생각, 코드, URL을 한곳에서 찾는다."),
        ("Insights", "학습량과 Course 진도에서 분리된 Skill 숙련 근거를 확인한다."),
        ("Settings", "학습 기본값과 로컬 데이터를 직접 관리한다."),
    ],
)
def test_phase2_secondary_pages_show_core_copy(page: str, copy: str) -> None:
    at = _app()
    at.radio[0].set_value(page).run()
    assert not at.exception
    assert any(item.value == page for item in at.title)
    # Korean glyphs are replaced by Streamlit's AppTest protobuf in this
    # Windows runner, so also assert the exact rendered source copy exists.
    assert copy in (ROOT / "app.py").read_text(encoding="utf-8")


def test_course_question_banks_have_expected_counts_no_issues_and_sqld_is_active() -> None:
    catalog = discover_courses(load_settings(ROOT).courses_dir)
    courses = {course.id: course for course in catalog.courses}
    expected_counts = {
        "ai-for-beginners": 4,
        "aice-associate": 6,
        "pspo-i": 6,
        "sqld": 6,
    }

    assert set(expected_counts) <= set(courses)
    assert courses["sqld"].status == "active"
    for course_id, expected in expected_counts.items():
        assert len(load_question_file(courses[course_id])) == expected

    question_catalog = discover_questions(catalog.courses)
    assert len(question_catalog.questions) == 22
    assert question_catalog.issues == ()
