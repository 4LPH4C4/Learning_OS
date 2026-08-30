from __future__ import annotations

import json
from pathlib import Path

from learning_os.config import load_settings
from learning_os.core.catalog import discover_courses
from learning_os.core.practice import profile_for, select_questions
from learning_os.core.question_bank import discover_questions


ROOT = Path(__file__).parents[1]


def _catalogs():
    course_catalog = discover_courses(load_settings(ROOT).courses_dir)
    question_catalog = discover_questions(course_catalog.courses)
    assert course_catalog.issues == ()
    assert question_catalog.issues == ()
    return (
        {course.id: course for course in course_catalog.courses},
        question_catalog,
    )


def _assert_markdown_lessons_are_substantial(course_id: str, courses) -> None:
    course = courses[course_id]
    for lesson in course.lessons:
        if lesson.type != "markdown":
            continue
        path = course.root_path / str(lesson.content_path)
        content = path.read_text(encoding="utf-8")
        assert len(path.read_bytes()) >= 600, f"{path} 학습 내용이 너무 짧다"
        assert content.lstrip().startswith("#"), f"{path}에 제목이 필요하다"


def test_pspo_curriculum_covers_the_official_focus_areas_and_full_mock() -> None:
    courses, questions = _catalogs()
    course = courses["pspo-i"]
    bank = questions.for_course(course.id)
    lesson_ids = {lesson.id for lesson in course.lessons}
    required_lessons = {
        "assessment-blueprint",
        "scrum-theory-and-empiricism",
        "scrum-team-accountabilities",
        "scrum-events",
        "artifacts-commitments-done",
        "product-vision-strategy-goal",
        "product-value-and-evidence",
        "customers-stakeholders-discovery",
        "product-backlog-management",
        "refinement-ordering-slicing",
        "forecasting-release-planning",
        "product-owner-leadership",
        "capstone-product-operating-system",
    }

    assert len(course.modules) == 7
    assert len(course.lessons) == 16
    assert required_lessons <= lesson_ids
    assert len(bank) == 80
    assert len({question.id for question in bank}) == 80
    assert len({question.prompt.casefold() for question in bank}) == 80
    assert all(question.source_ref for question in bank)
    assert {question.type for question in bank} == {"single_choice", "multiple_choice"}

    profile = profile_for(course, "mock_exam")
    assert (profile.question_count, profile.duration_minutes, profile.target_score) == (80, 60, 90)
    selected = select_questions(bank, count=profile.question_count, seed="pspo-release-gate")
    assert len(selected) == 80
    assert len({question.id for question in selected}) == 80
    _assert_markdown_lessons_are_substantial(course.id, courses)


def test_aice_curriculum_covers_the_official_practical_pipeline() -> None:
    courses, questions = _catalogs()
    course = courses["aice-associate"]
    bank = questions.for_course(course.id)
    lesson_ids = {lesson.id for lesson in course.lessons}
    required_lessons = {
        "associate-exam-overview",
        "python-environment-and-loading",
        "data-schema-and-quality",
        "exploratory-analysis-with-pandas",
        "missing-and-outlier-treatment",
        "encoding-and-scaling",
        "leakage-and-reproducibility",
        "classification-and-regression",
        "neural-network-simulation",
        "model-improvement-and-graphing",
        "associate-end-to-end-lab",
    }

    assert len(course.modules) == 5
    assert len(course.lessons) == 17
    assert required_lessons <= lesson_ids
    assert len(bank) == 28
    assert len({question.id for question in bank}) == 28
    assert all(question.source_ref for question in bank)
    assert {
        "data-quality",
        "data-visualization",
        "data-preprocessing",
        "machine-learning",
        "model-evaluation",
        "deep-learning",
        "ml-reproducibility",
    } <= {question.skill_id for question in bank}
    assert {question.type for question in bank} == {
        "single_choice",
        "multiple_choice",
        "short_answer",
    }

    profile = profile_for(course, "mock_exam")
    assert (profile.question_count, profile.duration_minutes, profile.target_score) == (14, 90, 80)
    _assert_markdown_lessons_are_substantial(course.id, courses)


def test_aice_end_to_end_notebook_is_clean_and_runs_top_to_bottom(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("MPLBACKEND", "Agg")
    monkeypatch.setenv("MPLCONFIGDIR", str(tmp_path / "matplotlib"))
    path = ROOT / "courses" / "aice-associate" / "notebooks" / "associate-end-to-end.ipynb"
    notebook = json.loads(path.read_text(encoding="utf-8"))

    assert notebook["nbformat"] == 4
    assert len(notebook["cells"]) >= 12
    assert all(cell.get("id") for cell in notebook["cells"])
    code_cells = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
    assert all(cell.get("execution_count") is None for cell in code_cells)
    assert all(cell.get("outputs") == [] for cell in code_cells)

    namespace: dict[str, object] = {"__name__": "__main__"}
    for index, cell in enumerate(code_cells):
        source = "".join(cell.get("source", []))
        exec(compile(source, f"{path}#code-cell-{index}", "exec"), namespace)
