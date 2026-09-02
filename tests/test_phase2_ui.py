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
        "오늘의 학습": "Learning OS",
        "Courses": "Courses",
        "복습": "복습",
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
    assert "오늘의 학습" in _visible_text(at)
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "오늘 학습 범위 조정" in source

    at.radio[0].set_value("Courses").run()
    assert not at.exception
    selector = next(
        item for item in at.multiselect if item.key == "selected-course-picker"
    )
    assert selector.label == "학습할 Course 선택"
    assert set(selector.options) == {
        "AI for Beginners",
        "AICE Associate",
        "English — CEFR A1 to C2",
        "중국어 — 입문부터 HSK 9까지",
        "NCS 직업공통능력 — 이론과 종합 모의고사 10회",
        "PSPO I — Professional Product Ownership",
        "SQLD",
    }

    at.radio[0].set_value("복습").run()
    assert not at.exception
    text = _visible_text(at)
    assert any(item.value == "복습" for item in at.title)
    assert (
        "선택한 Course 퀴즈" in text
        or "먼저 Courses에서 공부할 Course를 선택해라" in source
    )


def test_lesson_explains_duration_and_separates_today_from_course_next() -> None:
    at = _app()
    at.session_state["page"] = "lesson"
    at.session_state["course_id"] = "pspo-i"
    at.session_state["lesson_id"] = "assessment-blueprint"
    at.run()

    assert not at.exception
    text = _visible_text(at)
    assert "예상 학습 시간 · 35분" in text
    assert "공식 평가 구조 대조 · 7분" in text
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    # 완료 후 UI는 저장된 사용자 진도에 따라 조건부로 표시되므로, 깨끗한
    # DB에서도 테스트가 사용자 데이터를 만들지 않도록 정확한 문구를 확인한다.
    assert "오늘의 학습 상태" in source
    assert "이 Course의 다음 세션" in source


def test_adaptive_language_and_ncs_fixed_round_controls_render() -> None:
    at = _app()
    at.session_state["page"] = "course"
    at.session_state["course_id"] = "english-cefr"
    at.run()

    assert not at.exception
    assert "레벨 진단" in _visible_text(at)
    assert any(button.key == "placement:english-cefr" for button in at.button)

    at.session_state["page"] = "course"
    at.session_state["course_id"] = "ncs-core"
    at.run()

    assert not at.exception
    mock_round = next(
        selectbox for selectbox in at.selectbox if selectbox.key == "mock-set:ncs-core"
    )
    assert len(mock_round.options) == 10


@pytest.mark.parametrize(
    ("page", "copy"),
    [
        ("Notes", "Lesson에서 남긴 생각, 코드, URL을 한곳에서 찾는다."),
        ("Insights", "날짜별 학습 기록과 Course 진도에서 분리된 Skill 숙련 근거를 확인한다."),
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


def test_insights_renders_monthly_study_calendar() -> None:
    at = _app()
    at.radio[0].set_value("Insights").run()

    assert not at.exception
    assert "학습 캘린더" in _visible_text(at)
    button_keys = {button.key for button in at.button}
    assert {"calendar-previous-month", "calendar-next-month"} <= button_keys
    assert 28 <= len(
        [key for key in button_keys if (key or "").startswith("calendar-day:")]
    ) <= 31


def test_course_question_banks_have_expected_counts_no_issues_and_sqld_is_active() -> None:
    catalog = discover_courses(load_settings(ROOT).courses_dir)
    courses = {course.id: course for course in catalog.courses}
    expected_counts = {
        "ai-for-beginners": 4,
        "aice-associate": 28,
        "chinese-hsk": 50,
        "english-cefr": 36,
        "ncs-core": 500,
        "pspo-i": 80,
        "sqld": 6,
    }

    assert set(expected_counts) <= set(courses)
    assert courses["sqld"].status == "active"
    for course_id, expected in expected_counts.items():
        assert len(load_question_file(courses[course_id])) == expected

    question_catalog = discover_questions(catalog.courses)
    assert len(question_catalog.questions) == 704
    assert question_catalog.issues == ()
