from __future__ import annotations

import calendar
from collections import defaultdict
import html
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

import streamlit as st


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from learning_os.core.glossary import (  # noqa: E402
    CourseGlossary,
    GlossaryError,
    GlossaryTerm,
    load_glossary,
    terms_in_content,
)
from learning_os.core.adaptive import (  # noqa: E402
    MockExamSet,
    PlacementResult,
    eligible_lessons,
    mock_exam_sets,
    personalize_course,
    placement_config,
    placement_result,
    placement_setting_key,
    recommend_placement,
)
from learning_os.core.insights import StudyActivity  # noqa: E402
from learning_os.core.course_selection import (  # noqa: E402
    SELECTED_COURSE_IDS_SETTING,
    normalize_selected_course_ids,
    selectable_courses,
    selected_courses,
)
from learning_os.core.models import (  # noqa: E402
    Course,
    Lesson,
    StudyRecommendation,
    StudyStep,
)
from learning_os.core.assessment import QuizQuestion, evaluate_answer  # noqa: E402
from learning_os.core.practice import (  # noqa: E402
    profile_for,
    profile_for_set,
    score_percent,
    select_questions,
)
from learning_os.core.scheduler import build_curriculum_plan  # noqa: E402
from learning_os.integrations.content_loader import (  # noqa: E402
    ContentUnavailableError,
    read_markdown,
    resolve_content_path,
    without_leading_title,
)
from learning_os.integrations.course_importer import CourseImporter, CourseImportError  # noqa: E402
from learning_os.integrations.ai_provider import (  # noqa: E402
    AIContext,
    AIProviderError,
    DisabledAIProvider,
)
from learning_os.integrations.backup import BackupError, BackupManager  # noqa: E402
from learning_os.integrations.github_source import (  # noqa: E402
    GitHubSourceManager,
    SourceError,
)
from learning_os.integrations.notebook_launcher import (  # noqa: E402
    NotebookLaunchError,
    launch_notebook,
)
from learning_os.database.daily_plan import DailyStudyPlanItem  # noqa: E402
from learning_os.services.learning_service import LearningRuntime, build_runtime  # noqa: E402
from learning_os.ui.glossary import annotate_markdown_with_glossary  # noqa: E402
from learning_os.ui.theme import apply_theme  # noqa: E402


st.set_page_config(page_title="Learning OS", page_icon="◒", layout="wide")
apply_theme()


@st.cache_resource
def runtime() -> LearningRuntime:
    return build_runtime()


def go(page: str, *, course_id: str | None = None, lesson_id: str | None = None) -> None:
    st.session_state.page = page
    top_level = {"dashboard", "courses", "review", "notes", "insights", "settings"}
    if page in top_level:
        target = page
    elif page == "practice":
        target = str(st.session_state.get("practice_parent", "review"))
    else:
        target = "courses"
    st.session_state._navigation_target = target
    if course_id is not None:
        st.session_state.course_id = course_id
    if lesson_id is not None:
        st.session_state.lesson_id = lesson_id
    st.rerun()


def open_lesson(app: LearningRuntime, course: Course, lesson: Lesson) -> None:
    app.progress.mark_started(course.id, lesson.id)
    session_key = f"session:{course.id}:{lesson.id}"
    if session_key not in st.session_state:
        st.session_state[session_key] = app.progress.start_session(course.id, lesson.id)
    go("lesson", course_id=course.id, lesson_id=lesson.id)


def start_practice_flow(
    app: LearningRuntime,
    questions: tuple[QuizQuestion, ...],
    *,
    mode: str,
    parent: str,
    duration_minutes: int | None = None,
    target_score: int | None = None,
    placement_course_id: str | None = None,
    placement_lesson_id: str | None = None,
    exam_set: MockExamSet | None = None,
) -> None:
    if not questions:
        st.warning("시작할 문항이 아직 없어. Course의 questions.yaml을 확인해라.")
        return
    course_ids = {question.course_id for question in questions}
    session_course = next(iter(course_ids)) if len(course_ids) == 1 else "mixed-review"
    session_id = app.learning.start_practice(session_course, mode, questions)
    st.session_state.practice_state = {
        "session_id": session_id,
        "mode": mode,
        "question_refs": [(question.course_id, question.id) for question in questions],
        "position": 0,
        "correct": 0,
        "correct_question_refs": [],
        "question_started": time.monotonic(),
        "practice_started": time.monotonic(),
        "duration_minutes": duration_minutes,
        "target_score": target_score,
        "placement_course_id": placement_course_id,
        "placement_lesson_id": placement_lesson_id,
        "exam_set_id": exam_set.id if exam_set else None,
        "exam_set_title": exam_set.title if exam_set else None,
    }
    st.session_state.practice_parent = parent
    st.session_state.pop("practice_feedback", None)
    go("practice")


def stored_placement_result(app: LearningRuntime, course: Course) -> PlacementResult | None:
    return placement_result(
        app.learning.get_setting(placement_setting_key(course.id)),
        course,
    )


def adaptive_course(app: LearningRuntime, course: Course) -> Course:
    return personalize_course(course, stored_placement_result(app, course))


def current_learning_level(
    app: LearningRuntime,
    course: Course,
    result: PlacementResult,
) -> str:
    statuses = app.progress.statuses()
    path = adaptive_course(app, course)
    next_level = next(
        (
            lesson.level
            for lesson in path.required_lessons
            if lesson.level is not None
            and statuses.get((course.id, lesson.id)) != "completed"
        ),
        None,
    )
    if next_level is not None:
        return next_level
    completed_levels = [lesson.level for lesson in path.lessons if lesson.level is not None]
    return completed_levels[-1] if completed_levels else result.level_id


def mock_result_setting_key(course_id: str, set_id: str) -> str:
    return f"mock-exam-result:{course_id}:{set_id}"


def start_placement_assessment(
    app: LearningRuntime,
    course: Course,
    *,
    parent: str = "courses",
) -> None:
    config = placement_config(course)
    if config is None:
        st.warning("이 Course에는 진단평가 설정이 없어.")
        return
    app.progress.mark_started(course.id, config.lesson_id)
    available = app.questions.for_set(course.id, config.question_set)
    questions = select_questions(
        available,
        count=min(config.question_count, len(available)),
        seed=f"{course.id}:{config.question_set}:v1",
    )
    if len(questions) < config.question_count:
        st.warning(
            f"진단 문항이 {len(questions)}개뿐이야. 설정된 {config.question_count}개를 확인해라."
        )
        return
    start_practice_flow(
        app,
        questions,
        mode="practice",
        parent=parent,
        duration_minutes=config.duration_minutes,
        placement_course_id=course.id,
        placement_lesson_id=config.lesson_id,
    )


def start_mock_exam_set(
    app: LearningRuntime,
    course: Course,
    exam_set: MockExamSet,
    *,
    parent: str = "courses",
) -> None:
    profile = profile_for_set(exam_set)
    available = app.questions.for_set(course.id, exam_set.id)
    questions = select_questions(
        available,
        count=min(profile.question_count, len(available)),
        seed=f"{course.id}:{exam_set.id}:fixed",
    )
    if len(questions) < profile.question_count:
        st.warning(
            f"{exam_set.title} 문항이 {len(questions)}개뿐이야. 설정된 {profile.question_count}개를 확인해라."
        )
        return
    start_practice_flow(
        app,
        questions,
        mode="mock_exam",
        parent=parent,
        duration_minutes=profile.duration_minutes,
        target_score=profile.target_score,
        exam_set=exam_set,
    )


def start_course_practice(
    app: LearningRuntime,
    course: Course,
    mode: str,
    *,
    parent: str = "courses",
) -> None:
    available = app.questions.for_course(course.id)
    placement = placement_config(course)
    if placement is not None:
        result = stored_placement_result(app, course)
        if result is None:
            st.info("먼저 레벨 진단평가를 완료해라.")
            return
        learning_level = current_learning_level(app, course, result)
        level_questions = tuple(
            question for question in available if question.level == learning_level
        )
        available = level_questions or tuple(
            question
            for question in available
            if placement.question_set not in question.sets
        )
    profile = profile_for(course, mode)
    weakness = {
        insight.topic: insight.weakness
        for insight in app.learning.topic_insights()
        if insight.course_id == course.id
    }
    questions = select_questions(
        available,
        count=min(profile.question_count, len(available)),
        seed=f"{date.today().isoformat()}:{mode}:{len(app.learning.topic_insights())}",
        weakness_by_topic=weakness,
    )
    start_practice_flow(
        app,
        questions,
        mode=mode,
        parent=parent,
        duration_minutes=profile.duration_minutes,
        target_score=profile.target_score,
    )


def progress_percent(app: LearningRuntime, course: Course) -> tuple[int, int, int]:
    completed, total = app.progress.progress_for(adaptive_course(app, course))
    percent = round(completed / total * 100) if total else 0
    return completed, total, percent


def schedule_summary(course: Course) -> str:
    schedule = course.schedule
    parts = []
    if schedule.start_date:
        parts.append(f"시작 {schedule.start_date.isoformat()}")
    if schedule.target_date:
        parts.append(f"목표 {schedule.target_date.isoformat()}")
    if schedule.exam_date:
        parts.append(f"시험 {schedule.exam_date.isoformat()}")
    if schedule.estimated_hours is not None:
        parts.append(f"예상 {schedule.estimated_hours:g}시간")
    if schedule.weekly_target_hours is not None:
        parts.append(f"주 {schedule.weekly_target_hours:g}시간")
    return " · ".join(parts) or "자율 일정"


def stored_study_minutes(app: LearningRuntime) -> int:
    value = app.learning.get_setting("default_study_minutes", 60)
    try:
        minutes = int(value)
    except (TypeError, ValueError):
        return 60
    return minutes if minutes in {15, 30, 45, 60, 90, 120} else 60


def stored_languages(app: LearningRuntime) -> set[str]:
    value = app.learning.get_setting("content_languages", ["ko", "en"])
    if not isinstance(value, list):
        return {"ko", "en"}
    result = {str(language) for language in value if language in {"ko", "en"}}
    return result or {"ko", "en"}


def stored_selected_course_ids(app: LearningRuntime) -> tuple[str, ...]:
    return normalize_selected_course_ids(
        app.catalog.courses,
        app.learning.get_setting(SELECTED_COURSE_IDS_SETTING, []),
    )


def inferred_study_steps(lesson: Lesson) -> tuple[StudyStep, ...]:
    if lesson.study_steps:
        return lesson.study_steps
    total = lesson.duration_minutes
    if lesson.type in {"notebook", "external_notebook", "markdown_notebook"}:
        first = max(2, round(total * 0.15))
        second = max(2, round(total * 0.4))
        third = max(2, round(total * 0.35))
        fourth = total - first - second - third
        if fourth <= 0:
            third += fourth - 1
            fourth = 1
        return (
            StudyStep("문제와 데이터 이해", first),
            StudyStep("예제 코드 실행", second),
            StudyStep("코드 수정·문제 해결", third),
            StudyStep("결과 검증과 회고", fourth),
        )
    first = max(2, round(total * 0.4))
    second = max(2, round(total * 0.25))
    third = total - first - second
    if third <= 0:
        second += third - 1
        third = 1
    return (
        StudyStep("핵심 이론 읽기", first),
        StudyStep("예시·오해 비교", second),
        StudyStep("자가점검·적용 기록", third),
    )


def render_study_time_plan(lesson: Lesson) -> None:
    with st.container(border=True):
        st.markdown(f"**예상 학습 시간 · {lesson.duration_minutes}분**")
        st.caption(
            "표시 시간은 문서를 읽는 시간만이 아니라, 이해 확인과 직접 적용까지 마치는 기준이야."
        )
        for step in inferred_study_steps(lesson):
            outcome = f" — {step.outcome}" if step.outcome else ""
            st.markdown(f"- **{step.label} · {step.duration_minutes}분**{outcome}")


def safe_glossary(course: Course) -> CourseGlossary:
    try:
        return load_glossary(course)
    except GlossaryError:
        return CourseGlossary(course_id=course.id)


def render_term_definition(
    term: GlossaryTerm,
    glossary: CourseGlossary,
    *,
    show_title: bool = True,
) -> None:
    if show_title:
        st.markdown(f"### {term.name}")
    st.markdown(f"**{term.short_definition}**")
    st.markdown(term.explanation)
    if term.example:
        st.caption("실제 적용 예시")
        st.markdown(term.example)
    related = [
        related.name
        for related_id in term.related_terms
        if (related := glossary.get(related_id)) is not None
    ]
    if related:
        st.caption(f"함께 보면 좋은 용어 · {' · '.join(related)}")
    if term.source_url:
        st.link_button("공식 자료 열기", term.source_url, icon=":material/open_in_new:")


def render_lesson_glossary(course: Course, content: str) -> None:
    glossary = safe_glossary(course)
    terms = terms_in_content(glossary, content, limit=10)
    if not terms:
        return
    st.subheader("이 Lesson의 핵심 용어")
    st.caption(
        "본문의 점선 용어를 누르면 읽던 자리에서 뜻을 확인할 수 있어. "
        "아래 버튼은 자세한 설명과 예시를 보여줘."
    )
    with st.container(horizontal=True):
        for term in terms:
            with st.popover(
                term.name,
                icon=":material/book_2:",
                key=f"term:{course.id}:{term.id}",
                width="content",
                wrap=True,
            ):
                render_term_definition(term, glossary)


@st.dialog("Course 용어사전", width="large", icon=":material/dictionary:")
def glossary_dialog(course: Course) -> None:
    glossary = safe_glossary(course)
    st.subheader(course.title)
    if not glossary.terms:
        st.info("이 Course에는 아직 용어사전이 없어.")
        return
    query = st.text_input(
        "용어 검색",
        placeholder="용어, 별칭, 설명에서 검색",
        key=f"glossary-search:{course.id}",
        icon=":material/search:",
    )
    matches = glossary.search(query)
    st.caption(f"{len(matches)}개 용어")
    for term in matches:
        with st.expander(term.name):
            render_term_definition(term, glossary, show_title=False)


def render_progress(app: LearningRuntime, course: Course) -> None:
    completed, total, percent = progress_percent(app, course)
    status_class = "" if course.status == "active" else " planned"
    status_label = "진행 중" if course.status == "active" else "준비 예정"
    st.markdown(
        f"""
        <div class="course-row">
          <div class="study-course"><span class="status-dot{status_class}"></span>{html.escape(status_label)}</div>
          <div class="study-title">{html.escape(course.title)}</div>
          <div class="study-meta">{completed}/{total}개 완료 · {percent}% · {html.escape(schedule_summary(course))}</div>
          <div class="progress-track"><div class="progress-fill" style="width:{percent}%"></div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_source_status(app: LearningRuntime, course: Course) -> None:
    github_sources = [source for source in course.content_sources if source.type == "github"]
    if not github_sources:
        return
    manager = GitHubSourceManager(app.settings)
    st.subheader("Original Source")
    for source in github_sources:
        state = manager.inspect(course, source)
        if state.available:
            commit = (state.commit_sha or "unknown")[:8]
            st.caption(f"연결됨 · commit {commit} · 마지막 sync {state.last_sync_at or '확인 불가'}")
            action = "원본 업데이트"
        else:
            st.warning("원본 Course가 아직 준비되지 않았어. 다른 Course는 그대로 학습할 수 있어.")
            action = "원본 준비"
        if st.button(action, key=f"source:{course.id}:{source.id}"):
            with st.spinner("Microsoft 원본 Course를 동기화하는 중이야…"):
                try:
                    updated = manager.sync(course, source)
                    app.progress.save_source_state(updated)
                except SourceError as exc:
                    failed = manager.inspect(course, source)
                    failed = failed.__class__(
                        source_id=failed.source_id,
                        course_id=failed.course_id,
                        status="error",
                        local_path=failed.local_path,
                        repository_url=failed.repository_url,
                        commit_sha=failed.commit_sha,
                        last_sync_at=failed.last_sync_at,
                        error_message=str(exc),
                        available=False,
                    )
                    app.progress.save_source_state(failed)
                    st.error(f"원본 동기화에 실패했어: {exc}")
                else:
                    st.success("원본 Course를 준비했어.")
                    st.rerun()


def next_required_lesson(
    app: LearningRuntime,
    course: Course,
    statuses: dict[tuple[str, str], str],
    allowed_languages: set[str],
) -> Lesson | None:
    course = adaptive_course(app, course)
    return next(
        (
            lesson
            for lesson in course.required_lessons
            if (lesson.language is None or lesson.language in allowed_languages)
            and statuses.get((course.id, lesson.id)) != "completed"
        ),
        None,
    )


def resolve_daily_recommendations(
    app: LearningRuntime,
    items: tuple[DailyStudyPlanItem, ...],
) -> tuple[StudyRecommendation, ...]:
    resolved = []
    for item in items:
        course = app.course(item.course_id)
        lesson = app.lesson(item.course_id, item.lesson_id)
        if (
            course is not None
            and lesson is not None
            and lesson in eligible_lessons(course, stored_placement_result(app, course))
        ):
            resolved.append(
                StudyRecommendation(course=course, lesson=lesson, reason="오늘 계획에 고정")
            )
    return tuple(resolved)


def render_recommendation(
    app: LearningRuntime,
    item: StudyRecommendation,
    index: int,
    total: int,
    *,
    completed: bool,
    is_next: bool,
) -> None:
    left, right = st.columns([5, 1.35], vertical_alignment="center")
    with left:
        state_label = "완료" if completed else ("다음" if is_next else "예정")
        st.markdown(
            f"""
            <div class="study-row">
              <div class="study-course">오늘 {index + 1}/{total} · {state_label} · {html.escape(item.course.title)}</div>
              <div class="study-title">{html.escape(item.lesson.title)}</div>
              <div class="study-meta">{item.lesson.duration_minutes}분 · {html.escape(item.reason)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        if st.button(
            "다시 보기" if completed else ("지금 시작" if is_next else "열기"),
            key=f"start:{item.course.id}:{item.lesson.id}:{index}",
            type="primary" if is_next else "secondary",
            width="stretch",
        ):
            open_lesson(app, item.course, item.lesson)


def dashboard(app: LearningRuntime) -> None:
    current_date = date.today()
    today_id = current_date.isoformat()
    today_text = current_date.strftime("%Y.%m.%d")
    selected_ids = stored_selected_course_ids(app)
    learning_courses = selected_courses(app.catalog.courses, selected_ids)
    selected_id_set = set(selected_ids)
    st.markdown(f'<div class="eyebrow">TODAY · {today_text}</div>', unsafe_allow_html=True)
    st.title("Learning OS")
    st.markdown(
        '<div class="page-lead">오늘 할 일을 고르는 시간을 줄이고, 한 Lesson씩 실제 역량을 쌓는다.</div>',
        unsafe_allow_html=True,
    )

    statuses = app.progress.statuses()
    completed_today = sum(
        1
        for item in app.progress.completed_lessons_on(today_id)
        if item.course_id in selected_id_set
    )
    due_reviews = tuple(
        item
        for item in app.due_reviews()
        if item.question.course_id in selected_id_set
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f'<div class="metric-number">{completed_today}</div><div class="metric-label">완료 Lesson</div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="metric-number">{len(learning_courses)}</div><div class="metric-label">선택 Course</div>', unsafe_allow_html=True)
    with c3:
        st.markdown(
            f'<div class="metric-number">{len(due_reviews)}</div><div class="metric-label">복습 예정</div>',
            unsafe_allow_html=True,
        )

    if not learning_courses:
        st.header("오늘의 학습")
        st.info("먼저 Courses에서 공부할 Course를 선택해라. 선택한 Course만 오늘 계획과 복습에 포함돼.")
        if st.button("Courses에서 학습 Course 선택", type="primary", width="stretch"):
            go("courses")
        return

    if due_reviews:
        st.header("오늘의 복습")
        st.caption("기억이 흐려지기 전에 짧게 확인할 문항이야.")
        if st.button(
            f"복습 {min(len(due_reviews), 10)}문항 시작",
            type="primary",
            key="dashboard-review",
        ):
            start_practice_flow(
                app,
                tuple(item.question for item in due_reviews[:10]),
                mode="review",
                parent="dashboard",
            )

    st.header("오늘의 학습")
    saved_plan = app.progress.load_daily_plan(today_id)
    default_minutes = saved_plan.available_minutes if saved_plan else stored_study_minutes(app)
    minutes_key = f"study-minutes:{today_id}"
    st.session_state.setdefault(minutes_key, default_minutes)
    available = st.segmented_control(
        "오늘 가능한 시간",
        options=[15, 30, 45, 60, 90, 120],
        format_func=lambda value: f"{value}분",
        key=minutes_key,
    )
    available_minutes = int(available or default_minutes)
    allowed_languages = stored_languages(app)
    selection_basis_key = f"daily-plan-selection:{today_id}"
    stored_basis = app.learning.get_setting(selection_basis_key)
    normalized_basis = normalize_selected_course_ids(app.catalog.courses, stored_basis)
    selection_changed = (
        not isinstance(stored_basis, (list, tuple))
        or normalized_basis != selected_ids
    )
    if saved_plan is None or selection_changed:
        completed_before_plan = tuple(
            item
            for item in app.progress.completed_lessons_on(today_id)
            if item.course_id in selected_id_set
            and app.course(item.course_id) is not None
            and app.lesson(item.course_id, item.lesson_id) is not None
        )
        retained_items = tuple(
            item
            for item in (saved_plan.items if saved_plan else completed_before_plan)
            if item.course_id in selected_id_set
            and app.course(item.course_id) is not None
            and app.lesson(item.course_id, item.lesson_id) is not None
        )
        represented_course_ids = {item.course_id for item in retained_items}
        courses_to_add = tuple(
            course
            for course in learning_courses
            if course.id not in represented_course_ids
        )
        retained_minutes = sum(
            lesson.duration_minutes
            for item in retained_items
            if (lesson := app.lesson(item.course_id, item.lesson_id)) is not None
        )
        remaining_budget = max(0, available_minutes - retained_minutes)
        initial = (
            build_curriculum_plan(
                tuple(adaptive_course(app, course) for course in courses_to_add),
                statuses,
                remaining_budget,
                weakness_by_course=app.learning.weakness_by_course(),
                allowed_languages=allowed_languages,
            )
            if courses_to_add and remaining_budget > 0
            else ()
        )
        initial_items = retained_items + tuple(
            DailyStudyPlanItem(item.course.id, item.lesson.id) for item in initial
        )
        saved_plan = app.progress.save_daily_plan(
            today_id,
            available_minutes,
            initial_items,
        )
        app.learning.set_setting(selection_basis_key, list(selected_ids))
    elif saved_plan.available_minutes != available_minutes:
        saved_plan = app.progress.save_daily_plan(
            today_id,
            available_minutes,
            saved_plan.items,
        )

    valid_items = tuple(
        item
        for item in saved_plan.items
        if item.course_id in selected_id_set
        and (course := app.course(item.course_id)) is not None
        and app.lesson(item.course_id, item.lesson_id) is not None
        and item.lesson_id
        in {
            lesson.id
            for lesson in eligible_lessons(
                course,
                stored_placement_result(app, course),
            )
        }
    )
    if valid_items != saved_plan.items:
        saved_plan = app.progress.save_daily_plan(today_id, available_minutes, valid_items)

    if st.button(
        "가능한 시간에 맞춰 다시 추천",
        key=f"recommend-plan:{today_id}",
        icon=":material/refresh:",
    ):
        refreshed = build_curriculum_plan(
            tuple(adaptive_course(app, course) for course in learning_courses),
            statuses,
            available_minutes,
            weakness_by_course=app.learning.weakness_by_course(),
            allowed_languages=allowed_languages,
        )
        saved_plan = app.progress.save_daily_plan(
            today_id,
            available_minutes,
            [(item.course.id, item.lesson.id) for item in refreshed],
        )
        st.session_state[f"daily-plan-courses:{today_id}"] = list(
            dict.fromkeys(item.course.id for item in refreshed)
        )

    selectable_ids = [course.id for course in learning_courses]
    course_by_id = {course.id: course for course in learning_courses}
    course_key = f"daily-plan-courses:{today_id}"
    st.session_state.setdefault(
        course_key,
        list(dict.fromkeys(item.course_id for item in saved_plan.items)),
    )
    daily_course_ids = st.multiselect(
        "오늘 학습 범위 조정",
        options=selectable_ids,
        format_func=lambda course_id: (
            course_by_id[course_id].title
            + (" · 준비 예정" if course_by_id[course_id].status == "planned" else "")
        ),
        key=course_key,
        help="Courses에서 선택한 항목 중 오늘 공부할 Course를 조정할 수 있어.",
    )

    selected_set = set(daily_course_ids)
    adjusted_items = [
        item for item in saved_plan.items if item.course_id in selected_set
    ]
    courses_with_item = {item.course_id for item in adjusted_items}
    unavailable_courses: list[str] = []
    for course_id in daily_course_ids:
        if course_id in courses_with_item:
            continue
        course = course_by_id[course_id]
        next_lesson = next_required_lesson(app, course, statuses, allowed_languages)
        if next_lesson is None:
            unavailable_courses.append(course.title)
            continue
        adjusted_items.append(DailyStudyPlanItem(course.id, next_lesson.id))
        courses_with_item.add(course.id)
    adjusted_tuple = tuple(adjusted_items)
    if adjusted_tuple != saved_plan.items:
        saved_plan = app.progress.save_daily_plan(
            today_id,
            available_minutes,
            adjusted_tuple,
        )
    if unavailable_courses:
        st.info(f"추가할 미완료 Lesson이 없는 Course · {' · '.join(unavailable_courses)}")

    planned_refs = {(item.course_id, item.lesson_id) for item in saved_plan.items}
    additions: list[DailyStudyPlanItem] = []
    for course_id in daily_course_ids:
        course = course_by_id[course_id]
        candidate = next_required_lesson(app, course, statuses, allowed_languages)
        if candidate is not None and (course.id, candidate.id) not in planned_refs:
            additions.append(DailyStudyPlanItem(course.id, candidate.id))
    if additions and st.button(
        "선택한 Course의 다음 미완료 Lesson 추가",
        key=f"append-next-lessons:{today_id}",
        icon=":material/add:",
    ):
        saved_plan = app.progress.save_daily_plan(
            today_id,
            available_minutes,
            (*saved_plan.items, *additions),
        )
        st.rerun()

    recommendations = resolve_daily_recommendations(app, saved_plan.items)
    completed_refs = {
        (item.course.id, item.lesson.id)
        for item in recommendations
        if statuses.get((item.course.id, item.lesson.id)) == "completed"
    }
    total_minutes = sum(item.lesson.duration_minutes for item in recommendations)
    completed_count = len(completed_refs)
    completed_minutes = sum(
        item.lesson.duration_minutes
        for item in recommendations
        if (item.course.id, item.lesson.id) in completed_refs
    )
    remaining_minutes = total_minutes - completed_minutes
    st.subheader(f"오늘의 범위 · {completed_count}/{len(recommendations)} 완료")
    st.caption(
        "아래 Lesson만 오늘의 학습 범위야. 완료해도 목록은 자동으로 다음 Lesson으로 바뀌지 않아."
    )
    if recommendations:
        st.progress(completed_count / len(recommendations))
        st.caption(
            f"계획 {total_minutes}분 · 완료 {completed_minutes}분 · "
            f"남은 학습 {remaining_minutes}분 · 설정한 시간 {available_minutes}분"
        )
        remaining_budget = max(0, available_minutes - completed_minutes)
        if remaining_minutes > remaining_budget:
            st.warning("남은 학습이 오늘의 남은 시간보다 길어. Course를 줄이거나 가능한 시간을 늘려라.")
        remaining = tuple(
            item
            for item in recommendations
            if (item.course.id, item.lesson.id) not in completed_refs
        )
        if remaining:
            if st.button("다음 오늘 Lesson 시작", type="primary", width="stretch"):
                first = remaining[0]
                open_lesson(app, first.course, first.lesson)
        else:
            st.success("오늘 계획을 모두 완료했어. 더 학습하려면 위에서 Course를 다시 조정해라.")
        next_ref = (
            (remaining[0].course.id, remaining[0].lesson.id) if remaining else None
        )
        for index, item in enumerate(recommendations):
            ref = (item.course.id, item.lesson.id)
            render_recommendation(
                app,
                item,
                index,
                len(recommendations),
                completed=ref in completed_refs,
                is_next=ref == next_ref,
            )
    else:
        st.info("오늘 범위가 비어 있어. 위의 ‘오늘 학습 범위 조정’에서 Course를 선택해라.")

    st.header("선택한 Course 진도")
    for course in learning_courses:
        render_progress(app, course)
        if st.button("Course 열기", key=f"course:{course.id}"):
            go("course", course_id=course.id)

    if app.catalog.issues:
        with st.expander(f"불러오지 못한 Course {len(app.catalog.issues)}개"):
            for issue in app.catalog.issues:
                st.error(f"{issue.manifest_path.name}: {issue.message}")


def courses_page(app: LearningRuntime) -> None:
    st.markdown('<div class="eyebrow">CURRICULUM</div>', unsafe_allow_html=True)
    st.title("Courses")
    st.markdown('<div class="page-lead">공부할 Course를 고르면 오늘의 학습과 복습이 그 선택에 맞춰 구성된다.</div>', unsafe_allow_html=True)
    available_courses = selectable_courses(app.catalog.courses)
    available_ids = [course.id for course in available_courses]
    course_by_id = {course.id: course for course in available_courses}
    stored_ids = stored_selected_course_ids(app)
    chosen_ids = st.multiselect(
        "학습할 Course 선택",
        options=available_ids,
        default=list(stored_ids),
        format_func=lambda course_id: (
            course_by_id[course_id].title
            + (" · 준비 예정" if course_by_id[course_id].status == "planned" else "")
        ),
        help="선택은 로컬에 저장되고 오늘의 학습과 복습에 함께 적용돼.",
        key="selected-course-picker",
    )
    normalized_ids = normalize_selected_course_ids(app.catalog.courses, chosen_ids)
    if normalized_ids != stored_ids:
        app.learning.set_setting(SELECTED_COURSE_IDS_SETTING, list(normalized_ids))
        st.success("학습 Course 선택을 저장했어. 오늘의 학습과 복습에 바로 반영돼.")
    selected_id_set = set(normalized_ids)
    st.caption(f"선택 {len(normalized_ids)}개 · 언제든 다시 바꿀 수 있어.")
    st.divider()
    for course in app.catalog.courses:
        left, right = st.columns([5, 1.25], vertical_alignment="center")
        with left:
            render_progress(app, course)
            st.caption(course.description)
            if course.id in selected_id_set:
                st.caption("오늘의 학습 · 복습에 포함")
            elif course.status != "disabled":
                st.caption("학습 Course로 선택하지 않음")
        with right:
            if st.button("살펴보기", key=f"browse:{course.id}", width="stretch"):
                go("course", course_id=course.id)


def course_page(app: LearningRuntime, course: Course) -> None:
    if st.button("← Courses", key="back-courses"):
        go("courses")
    st.markdown(f'<div class="eyebrow">{html.escape(course.category)}</div>', unsafe_allow_html=True)
    st.title(course.title)
    st.markdown(f'<div class="page-lead">{html.escape(course.description)}</div>', unsafe_allow_html=True)
    st.caption(schedule_summary(course))
    completed, total, percent = progress_percent(app, course)
    st.write(f"{completed}/{total}개 완료 · {percent}%")
    st.progress(percent / 100 if total else 0)
    if safe_glossary(course).terms:
        if st.button(
            "Course 용어사전",
            key=f"glossary:{course.id}",
            icon=":material/dictionary:",
        ):
            glossary_dialog(course)
    if course.status == "planned":
        st.info("이 Course는 아직 준비 예정 상태야.")

    render_source_status(app, course)

    placement = placement_config(course)
    result = stored_placement_result(app, course)
    learning_course = adaptive_course(app, course)
    course_questions = app.questions.for_course(course.id)
    if placement is not None:
        st.subheader("레벨 진단")
        if result is None:
            st.info(
                f"첫 학습은 {placement.question_count}문항 진단평가야. "
                "결과에 맞는 단계부터 학습 경로가 열려."
            )
            placement_label = "진단평가 시작"
        else:
            st.success(
                f"권장 시작 단계 · {result.level_label} · "
                f"{result.score_percent}% ({result.correct_count}/{result.question_count})"
            )
            st.caption(
                "이 결과는 코스 난이도를 정하기 위한 진단이야. 공인 성적이나 말하기·듣기 "
                "능력 전체를 대신하지 않아. 진단 전 단계는 학습 경로에서 숨겼어."
            )
            placement_label = "진단평가 다시 보기"
        if st.button(
            placement_label,
            type="primary" if result is None else "secondary",
            key=f"placement:{course.id}",
        ):
            start_placement_assessment(app, course)

    exam_sets = mock_exam_sets(course)
    if course_questions and (placement is None or result is not None):
        st.subheader("Practice")
        if exam_sets:
            selected_set_id = st.selectbox(
                "종합 모의고사 회차",
                options=[item.id for item in exam_sets],
                format_func=lambda set_id: next(
                    item.title for item in exam_sets if item.id == set_id
                ),
                key=f"mock-set:{course.id}",
            )
            selected_set = next(item for item in exam_sets if item.id == selected_set_id)
            actual_count = len(app.questions.for_set(course.id, selected_set.id))
            st.caption(
                f"{actual_count}문항 · {selected_set.duration_minutes}분 · "
                f"목표 {selected_set.target_score}% · 각 회차는 고정 문항으로 다시 풀 수 있어."
            )
            latest_result = app.learning.get_setting(
                mock_result_setting_key(course.id, selected_set.id)
            )
            if isinstance(latest_result, dict):
                st.info(
                    f"최근 결과 · {latest_result.get('score_percent', 0)}% · "
                    f"{latest_result.get('correct_count', 0)}/{latest_result.get('question_count', 0)}"
                )
            quiz_col, mock_col = st.columns(2)
            with quiz_col:
                if st.button("빠른 Quiz", width="stretch", key=f"quiz:{course.id}"):
                    start_course_practice(app, course, "quiz")
            with mock_col:
                if st.button(
                    f"{selected_set.title} 시작",
                    type="primary",
                    width="stretch",
                    key=f"mock:{course.id}:{selected_set.id}",
                ):
                    start_mock_exam_set(app, course, selected_set)
        elif placement is not None:
            learning_level = current_learning_level(app, course, result) if result else ""
            level_label = next(
                (
                    item.label
                    for item in placement.levels
                    if item.id == learning_level
                ),
                learning_level,
            )
            current_count = (
                sum(question.level == learning_level for question in course_questions)
                if result
                else 0
            )
            st.caption(f"현재 학습 단계 {level_label} · {current_count}개 문항")
            if st.button(
                "현재 레벨 Quiz",
                type="primary",
                width="stretch",
                key=f"quiz:{course.id}",
            ):
                start_course_practice(app, course, "quiz")
        else:
            profile = profile_for(course, "mock_exam")
            st.caption(
                f"문항 은행 {len(course_questions)}개 · Mock 목표 {profile.target_score}%"
                + (f" · {profile.duration_minutes}분" if profile.duration_minutes else "")
            )
            quiz_col, mock_col = st.columns(2)
            with quiz_col:
                if st.button("빠른 Quiz", type="primary", width="stretch", key=f"quiz:{course.id}"):
                    start_course_practice(app, course, "quiz")
            with mock_col:
                if st.button("Mock Exam", width="stretch", key=f"mock:{course.id}"):
                    start_course_practice(app, course, "mock_exam")

    allowed_languages = stored_languages(app)
    course_statuses = app.progress.statuses()
    next_lesson = next_required_lesson(app, course, course_statuses, allowed_languages)
    for module in learning_course.modules:
        st.header(module.title)
        visible_lessons = tuple(
            lesson
            for lesson in module.lessons
            if lesson.language is None or lesson.language in allowed_languages
        )
        if not visible_lessons:
            st.caption("선택한 콘텐츠 언어에 해당하는 Lesson이 없어.")
        for lesson in visible_lessons:
            status = course_statuses.get((course.id, lesson.id))
            left, right = st.columns([5, 1.25], vertical_alignment="center")
            with left:
                if status == "completed":
                    marker = "완료"
                elif status == "started":
                    marker = "진행 중"
                elif next_lesson is not None and lesson.id == next_lesson.id:
                    marker = "다음 학습"
                else:
                    marker = "예정"
                st.markdown(
                    f'<div class="study-row"><div class="study-course">{html.escape(marker)}</div>'
                    f'<div class="study-title">{html.escape(lesson.title)}</div>'
                    f'<div class="study-meta">{lesson.duration_minutes}분 · {html.escape(lesson.type)}</div></div>',
                    unsafe_allow_html=True,
                )
            with right:
                if lesson.type in {"quiz", "practice", "mock_exam"}:
                    label = "연습 시작"
                else:
                    label = "열기"
                if st.button(label, key=f"lesson:{course.id}:{lesson.id}", width="stretch"):
                    if lesson.type in {"quiz", "practice", "mock_exam"}:
                        if placement is not None and lesson.id == placement.lesson_id:
                            start_placement_assessment(app, course)
                            continue
                        lesson_questions = tuple(
                            question
                            for question in course_questions
                            if question.lesson_id in {None, lesson.id}
                        )
                        mode = "mock_exam" if lesson.type == "mock_exam" else "practice"
                        start_practice_flow(app, lesson_questions, mode=mode, parent="courses")
                        continue
                    open_lesson(app, course, lesson)


def render_completed_lesson_next_steps(
    app: LearningRuntime,
    course: Course,
    lesson: Lesson,
) -> None:
    today_id = date.today().isoformat()
    plan = app.progress.load_daily_plan(today_id)
    statuses = app.progress.statuses()
    today_items = resolve_daily_recommendations(app, plan.items) if plan else ()
    today_refs = {(item.course.id, item.lesson.id) for item in today_items}
    current_ref = (course.id, lesson.id)
    remaining = tuple(
        item
        for item in today_items
        if statuses.get((item.course.id, item.lesson.id)) != "completed"
    )

    st.subheader("오늘의 학습 상태")
    if current_ref in today_refs:
        completed_count = len(today_items) - len(remaining)
        if remaining:
            next_today = remaining[0]
            st.success(
                f"오늘 범위에서 이 Lesson을 완료했어. "
                f"{completed_count}/{len(today_items)}개 완료."
            )
            st.info(
                f"오늘의 다음 Lesson · {next_today.course.title} — "
                f"{next_today.lesson.title} ({next_today.lesson.duration_minutes}분)"
            )
            with st.container(horizontal=True):
                if st.button(
                    "다음 오늘 Lesson 시작",
                    type="primary",
                    key=f"next-today:{course.id}:{lesson.id}",
                ):
                    open_lesson(app, next_today.course, next_today.lesson)
                if st.button(
                    "오늘 화면으로 돌아가기",
                    key=f"back-today:{course.id}:{lesson.id}",
                ):
                    go("dashboard")
        else:
            st.success(f"오늘 계획 {len(today_items)}/{len(today_items)}개를 모두 완료했어.")
            if st.button(
                "오늘 화면으로 돌아가기",
                key=f"back-today-complete:{course.id}:{lesson.id}",
            ):
                go("dashboard")
    else:
        st.caption("이 Lesson은 오늘 계획 밖에서 완료했어. 오늘 범위는 ‘오늘’ 화면에서 확인할 수 있어.")
        if st.button(
            "오늘 범위 확인",
            key=f"view-today:{course.id}:{lesson.id}",
        ):
            go("dashboard")

    next_course_lesson = next_required_lesson(app, course, statuses, stored_languages(app))
    if next_course_lesson is not None:
        next_ref = (course.id, next_course_lesson.id)
        st.subheader("이 Course의 다음 세션")
        st.markdown(f"**{next_course_lesson.title}** · {next_course_lesson.duration_minutes}분")
        if next_ref in today_refs:
            st.caption("이 Lesson은 이미 오늘 범위에 포함돼 있어.")
        else:
            st.caption(
                "Course 순서상 다음 Lesson이지만 오늘 범위에는 포함되지 않아. "
                "열어도 오늘 계획이 자동으로 바뀌지는 않아."
            )
        if st.button(
            "Course 다음 Lesson 열기",
            key=f"next-course:{course.id}:{lesson.id}",
        ):
            open_lesson(app, course, next_course_lesson)
    else:
        st.success("이 Course의 필수 Lesson을 모두 완료했어.")


def lesson_page(app: LearningRuntime, course: Course, lesson: Lesson) -> None:
    if st.button(f"← {course.title}", key="back-course"):
        go("course", course_id=course.id)
    st.markdown(f'<div class="eyebrow">{html.escape(course.title)} · {lesson.duration_minutes} MIN</div>', unsafe_allow_html=True)
    st.title(lesson.title)
    status = app.progress.statuses().get((course.id, lesson.id))
    if status == "completed":
        st.success("완료한 Lesson이야. 언제든 다시 볼 수 있어.")
    render_study_time_plan(lesson)

    if lesson.url:
        st.link_button("외부 학습 자료 열기", lesson.url, type="primary")

    if lesson.type == "pdf" and lesson.content_path:
        try:
            document_path = resolve_content_path(course, lesson, app.settings.external_dir)
            st.download_button(
                "PDF 열기 또는 저장",
                data=document_path.read_bytes(),
                file_name=document_path.name,
                mime="application/pdf",
            )
        except (ContentUnavailableError, OSError) as exc:
            st.warning(str(exc))
    elif lesson.type == "listening" and lesson.content_path:
        try:
            audio_path = resolve_content_path(course, lesson, app.settings.external_dir)
            st.audio(str(audio_path))
        except ContentUnavailableError as exc:
            st.warning(str(exc))
    elif lesson.content_path:
        try:
            content = read_markdown(course, lesson, app.settings.external_dir)
            render_lesson_glossary(course, f"{lesson.title}\n{content}")
            lesson_body = without_leading_title(content)
            annotated_body = annotate_markdown_with_glossary(
                lesson_body,
                safe_glossary(course),
            )
            st.html(annotated_body)
        except ContentUnavailableError as exc:
            st.warning(str(exc))
            source = course.source(lesson.source_id)
            if source and source.type == "github":
                st.info("Course 화면에서 원본 source를 준비한 뒤 다시 열어라.")

    placement = placement_config(course)
    if placement is not None and lesson.id == placement.lesson_id:
        st.divider()
        st.caption(
            f"{placement.question_count}문항 · 제한 {placement.duration_minutes}분 · "
            "도움 없이 한 번에 풀어야 배치 결과가 정확해."
        )
        if st.button("레벨 진단평가 시작", type="primary", width="stretch"):
            start_placement_assessment(app, course)
        return

    if lesson.notebook_path:
        if not lesson.content_path:
            render_lesson_glossary(
                course,
                " ".join((lesson.title, *lesson.skills)),
            )
        st.divider()
        st.subheader("Hands-on Notebook")
        st.caption("JupyterLab에서 코드를 직접 실행하고 수정한다.")
        if st.button("Notebook 열기", type="primary", key=f"notebook:{course.id}:{lesson.id}"):
            try:
                notebook_path = resolve_content_path(
                    course, lesson, app.settings.external_dir, notebook=True
                )
                launch_notebook(notebook_path, app.settings.project_root)
                st.success("JupyterLab을 시작했어. 새 브라우저 탭을 확인해라.")
            except (ContentUnavailableError, NotebookLaunchError) as exc:
                st.error(str(exc))

    with st.expander("이 Lesson에 Note 남기기"):
        existing_notes = app.learning.notes(course_id=course.id, lesson_id=lesson.id)
        if existing_notes:
            for note in existing_notes:
                st.markdown(f"**{note.title}**")
                st.markdown(note.body_markdown)
        with st.form(f"lesson-note:{course.id}:{lesson.id}", clear_on_submit=True):
            note_title = st.text_input("제목", value=f"{lesson.title} 메모")
            note_body = st.text_area("Markdown Note", height=150)
            if st.form_submit_button("Note 저장", type="primary"):
                if note_body.strip():
                    app.learning.save_note(
                        title=note_title,
                        body_markdown=note_body,
                        course_id=course.id,
                        lesson_id=lesson.id,
                    )
                    st.success("Note를 저장했어.")
                    st.rerun()
                else:
                    st.warning("Note 내용을 입력해라.")

    with st.expander("AI Tutor (optional)"):
        st.caption("Provider를 설정하지 않은 기본 상태에서도 나머지 학습 기능은 그대로 동작해.")
        with st.form(f"ai-tutor:{course.id}:{lesson.id}"):
            tutor_prompt = st.text_input("이 Lesson에 관해 질문")
            if st.form_submit_button("질문 보내기"):
                try:
                    DisabledAIProvider().answer(
                        AIContext(
                            prompt=tutor_prompt,
                            course_id=course.id,
                            lesson_id=lesson.id,
                        )
                    )
                except AIProviderError as exc:
                    st.info(str(exc))

    st.divider()
    if status != "completed":
        if st.button("Lesson 완료", type="primary", width="stretch"):
            app.progress.mark_completed(course.id, lesson.id)
            session_key = f"session:{course.id}:{lesson.id}"
            session_id = st.session_state.pop(session_key, None)
            if session_id is not None:
                app.progress.complete_session(int(session_id))
            st.success("진도를 저장했어.")
            st.rerun()
    else:
        render_completed_lesson_next_steps(app, course, lesson)


def practice_page(app: LearningRuntime) -> None:
    state = st.session_state.get("practice_state")
    if not isinstance(state, dict):
        st.error("진행 중인 연습을 찾을 수 없어.")
        if st.button("복습으로 이동"):
            go("review")
        return

    refs = list(state.get("question_refs", []))
    position = int(state.get("position", 0))
    if state.get("completed") or position >= len(refs):
        total = len(refs)
        correct = int(state.get("correct", 0))
        score = score_percent(correct, total)
        target_score = int(state.get("target_score") or 0)
        placement_outcome: PlacementResult | None = None
        placement_course_id = state.get("placement_course_id")
        if placement_course_id:
            placement_course = app.course(str(placement_course_id))
            if placement_course is not None:
                correct_refs = {
                    (str(ref[0]), str(ref[1]))
                    for ref in state.get("correct_question_refs", [])
                    if isinstance(ref, (list, tuple)) and len(ref) == 2
                }
                correct_by_level: dict[str, int] = defaultdict(int)
                total_by_level: dict[str, int] = defaultdict(int)
                for ref_course_id, ref_question_id in refs:
                    placement_question = app.questions.get(
                        str(ref_course_id),
                        str(ref_question_id),
                    )
                    if placement_question is None or placement_question.level is None:
                        continue
                    total_by_level[placement_question.level] += 1
                    if (str(ref_course_id), str(ref_question_id)) in correct_refs:
                        correct_by_level[placement_question.level] += 1
                placement_outcome = recommend_placement(
                    placement_course,
                    score_percent=score,
                    correct_count=correct,
                    question_count=total,
                    correct_by_level=correct_by_level,
                    total_by_level=total_by_level,
                )
                if not state.get("placement_saved"):
                    app.learning.set_setting(
                        placement_setting_key(placement_course.id),
                        placement_outcome.as_dict(),
                    )
                    placement_lesson_id = state.get("placement_lesson_id")
                    if placement_lesson_id:
                        app.progress.mark_completed(
                            placement_course.id,
                            str(placement_lesson_id),
                        )
                        lesson_session_key = (
                            f"session:{placement_course.id}:{placement_lesson_id}"
                        )
                        lesson_session_id = st.session_state.pop(
                            lesson_session_key,
                            None,
                        )
                        if lesson_session_id is not None:
                            app.progress.complete_session(int(lesson_session_id))
                    state["placement_saved"] = True
                    st.session_state.practice_state = state

        eyebrow = "PLACEMENT COMPLETE" if placement_outcome else "PRACTICE COMPLETE"
        st.markdown(f'<div class="eyebrow">{eyebrow}</div>', unsafe_allow_html=True)
        st.title(f"{score}%")
        st.markdown(
            f'<div class="page-lead">{total}문항 중 {correct}문항을 맞혔어. '
            "오답과 낮은 자신감 문항은 복습 일정에 자동 반영됐어.</div>",
            unsafe_allow_html=True,
        )
        if placement_outcome is not None:
            st.success(f"권장 시작 단계 · {placement_outcome.level_label}")
            st.caption(
                "정답률 기반의 코스 배치 결과야. 듣기·말하기까지 포함한 공인 등급 판정은 아니며, "
                "필요하면 언제든 다시 진단할 수 있어."
            )
            if placement_outcome.level_scores:
                result_course = app.course(placement_outcome.course_id)
                config = placement_config(result_course) if result_course else None
                labels = (
                    {item.id: item.label for item in config.levels}
                    if config
                    else {}
                )
                with st.expander("단계별 진단 근거"):
                    for level_id, level_correct, level_total in placement_outcome.level_scores:
                        level_percent = score_percent(level_correct, level_total)
                        st.write(
                            f"{labels.get(level_id, level_id)} · "
                            f"{level_correct}/{level_total} · {level_percent}%"
                        )
        if target_score:
            if score >= target_score:
                st.success(f"목표 {target_score}%를 달성했어.")
            else:
                st.info(f"목표 {target_score}%까지 {target_score - score}%p 남았어.")
        exam_set_title = state.get("exam_set_title")
        if exam_set_title:
            exam_set_id = str(state.get("exam_set_id"))
            exam_course_id = str(refs[0][0]) if refs else ""
            if exam_course_id and exam_set_id and not state.get("exam_saved"):
                app.learning.set_setting(
                    mock_result_setting_key(exam_course_id, exam_set_id),
                    {
                        "course_id": exam_course_id,
                        "set_id": exam_set_id,
                        "score_percent": score,
                        "correct_count": correct,
                        "question_count": total,
                        "completed_at": datetime.now(timezone.utc).isoformat(
                            timespec="seconds"
                        ),
                    },
                )
                state["exam_saved"] = True
                st.session_state.practice_state = state
            st.info(f"완료한 회차 · {exam_set_title}")
        action_label = (
            "권장 단계에서 학습 시작"
            if placement_outcome
            else "복습에서 다음 일정 확인"
        )
        if st.button(action_label, type="primary"):
            st.session_state.pop("practice_state", None)
            st.session_state.pop("practice_feedback", None)
            if placement_outcome:
                go("course", course_id=placement_outcome.course_id)
            else:
                go("review")
        return

    course_id, question_id = refs[position]
    question = app.questions.get(str(course_id), str(question_id))
    if question is None:
        st.error("문항을 찾을 수 없어. questions.yaml을 다시 확인해라.")
        return

    mode_label = {
        "quiz": "Quick Quiz",
        "review": "복습",
        "practice": "Practice",
        "mock_exam": "Mock Exam",
    }.get(str(state.get("mode")), "Practice")
    if state.get("placement_course_id"):
        mode_label = "Placement Assessment"
    elif state.get("exam_set_title"):
        mode_label = str(state["exam_set_title"])
    st.markdown(f'<div class="eyebrow">{html.escape(mode_label)} · {position + 1}/{len(refs)}</div>', unsafe_allow_html=True)
    st.title(question.topic)
    st.progress((position + 1) / len(refs))
    duration_minutes = state.get("duration_minutes")
    if duration_minutes:
        elapsed = max(0.0, time.monotonic() - float(state["practice_started"]))
        remaining = max(0, int(float(duration_minutes) * 60 - elapsed))
        st.caption(f"제한 {duration_minutes}분 · 남은 시간 {remaining // 60:02d}:{remaining % 60:02d}")
        if remaining <= 0 and not state.get("completed"):
            app.learning.complete_practice(int(state["session_id"]))
            state["completed"] = True
            st.session_state.practice_state = state
            st.rerun()
    st.markdown(f"### {question.prompt}")
    feedback = st.session_state.get("practice_feedback")

    if not isinstance(feedback, dict):
        with st.form(f"answer:{state['session_id']}:{position}"):
            if question.type == "single_choice":
                submitted = st.radio(
                    "답",
                    options=[option.id for option in question.options],
                    format_func=question.option_text,
                    index=None,
                )
                answers = [submitted] if submitted else []
            elif question.type == "multiple_choice":
                answers = st.multiselect(
                    "답을 모두 선택",
                    options=[option.id for option in question.options],
                    format_func=question.option_text,
                )
            else:
                short_answer = st.text_input("답")
                answers = [short_answer] if short_answer.strip() else []
            confidence = st.segmented_control(
                "확신 정도",
                options=[1, 2, 3, 4, 5],
                default=3,
                format_func=lambda value: f"{value}",
            )
            submitted_form = st.form_submit_button("답 제출", type="primary")
        if submitted_form:
            if not answers:
                st.warning("답을 입력하거나 선택해라.")
            else:
                result = evaluate_answer(question, answers)
                elapsed = max(0.0, time.monotonic() - float(state["question_started"]))
                attempt_id, schedule = app.learning.record_attempt(
                    question,
                    answers,
                    correct=result.correct,
                    response_time_seconds=elapsed,
                    confidence=int(confidence or 3),
                )
                app.learning.attach_attempt(
                    int(state["session_id"]),
                    position,
                    attempt_id,
                    result.correct,
                )
                if result.correct:
                    state["correct"] = int(state.get("correct", 0)) + 1
                    correct_refs = list(state.get("correct_question_refs", []))
                    correct_refs.append((question.course_id, question.id))
                    state["correct_question_refs"] = correct_refs
                st.session_state.practice_state = state
                st.session_state.practice_feedback = {
                    "correct": result.correct,
                    "feedback": result.feedback,
                    "due_on": schedule.due_on,
                    "interval": schedule.interval_days,
                }
                st.rerun()
    else:
        if feedback["correct"]:
            st.success("정답이야.")
        else:
            st.error("다시 확인할 문항이야.")
        st.markdown(str(feedback["feedback"]))
        st.caption(f"다음 복습 {feedback['due_on']} · {feedback['interval']}일 간격")
        if question.source_ref:
            st.caption(f"근거: {question.source_ref}")
        is_last = position + 1 >= len(refs)
        if st.button("결과 보기" if is_last else "다음 문항", type="primary"):
            st.session_state.pop("practice_feedback", None)
            if is_last:
                app.learning.complete_practice(int(state["session_id"]))
                state["completed"] = True
            else:
                state["position"] = position + 1
                state["question_started"] = time.monotonic()
            st.session_state.practice_state = state
            st.rerun()


def review_page(app: LearningRuntime) -> None:
    st.markdown('<div class="eyebrow">RECALL</div>', unsafe_allow_html=True)
    st.title("복습")
    st.markdown(
        '<div class="page-lead">선택한 Course에서 전에 풀었던 문항을 퀴즈로 다시 확인한다.</div>',
        unsafe_allow_html=True,
    )
    selected_ids = stored_selected_course_ids(app)
    learning_courses = selected_courses(app.catalog.courses, selected_ids)
    selected_id_set = set(selected_ids)
    if not learning_courses:
        st.info("먼저 Courses에서 공부할 Course를 선택해라. 선택한 Course의 복습만 이곳에 모여.")
        if st.button("Courses에서 학습 Course 선택", type="primary", width="stretch"):
            go("courses")
        return

    due = tuple(
        item
        for item in app.due_reviews()
        if item.question.course_id in selected_id_set
    )
    if due:
        st.subheader(f"오늘의 복습 · {len(due)}문항")
        for item in due[:10]:
            st.markdown(
                f'<div class="study-row"><div class="study-course">{html.escape(item.question.course_id)}</div>'
                f'<div class="study-title">{html.escape(item.question.topic)}</div>'
                f'<div class="study-meta">마감 {item.schedule.due_on} · '
                f'{item.schedule.interval_days}일 간격 · 자신감 {item.schedule.last_confidence}/5</div></div>',
                unsafe_allow_html=True,
            )
        if st.button("오늘의 복습 시작", type="primary", width="stretch"):
            start_practice_flow(
                app,
                tuple(item.question for item in due[:10]),
                mode="review",
                parent="review",
            )
    else:
        st.success("오늘 마감인 복습은 없어. 빠른 Quiz로 새 복습 주기를 만들 수 있어.")

    st.subheader("선택한 Course 퀴즈")
    st.caption("새 문항을 풀면 결과와 확신 정도를 바탕으로 다음 복습 일정이 생성돼.")
    for course in learning_courses:
        count = len(app.questions.for_course(course.id))
        if not count:
            continue
        left, right = st.columns([5, 1.25], vertical_alignment="center")
        with left:
            st.markdown(
                f'<div class="study-row"><div class="study-course">{html.escape(course.category)}</div>'
                f'<div class="study-title">{html.escape(course.title)}</div>'
                f'<div class="study-meta">{count}개 문항</div></div>',
                unsafe_allow_html=True,
            )
        with right:
            if st.button("Quiz 시작", key=f"review-quiz:{course.id}", width="stretch"):
                start_course_practice(app, course, "quiz", parent="review")

    if app.questions.issues:
        with st.expander(f"불러오지 못한 문항 파일 {len(app.questions.issues)}개"):
            for issue in app.questions.issues:
                st.error(f"{issue.path.name}: {issue.message}")


def notes_page(app: LearningRuntime) -> None:
    st.markdown('<div class="eyebrow">KNOWLEDGE BASE</div>', unsafe_allow_html=True)
    st.title("Notes")
    st.markdown(
        '<div class="page-lead">Lesson에서 남긴 생각, 코드, URL을 한곳에서 찾는다.</div>',
        unsafe_allow_html=True,
    )
    query = st.text_input("전체 검색", placeholder="제목, 본문, URL 검색")
    with st.expander("새 Note 작성"):
        with st.form("global-note", clear_on_submit=True):
            title = st.text_input("제목")
            body = st.text_area("Markdown Note", height=180)
            source_url = st.text_input("참고 URL (선택)")
            course_options = [""] + [course.id for course in app.catalog.courses]
            note_course = st.selectbox(
                "Course (선택)",
                options=course_options,
                format_func=lambda course_id: (
                    app.course(course_id).title if course_id and app.course(course_id) else "전체"
                ),
            )
            if st.form_submit_button("Note 저장", type="primary"):
                try:
                    app.learning.save_note(
                        title=title,
                        body_markdown=body,
                        course_id=note_course or None,
                        source_url=source_url or None,
                    )
                except ValueError as exc:
                    st.warning(str(exc))
                else:
                    st.success("Note를 저장했어.")
                    st.rerun()

    notes = app.learning.notes(query)
    if not notes:
        st.info("검색 결과가 없어." if query else "아직 Note가 없어.")
    for note in notes:
        context = " · ".join(item for item in (note.course_id, note.lesson_id) if item) or "전체"
        with st.expander(f"{note.title} · {context}"):
            st.markdown(note.body_markdown or "_내용 없음_")
            if note.source_url:
                st.link_button("참고 링크", note.source_url)
            st.caption(f"마지막 수정 {note.updated_at}")
            if st.button("삭제", key=f"delete-note:{note.id}"):
                app.learning.delete_note(note.id)
                st.rerun()


def insights_page(app: LearningRuntime) -> None:
    st.markdown('<div class="eyebrow">EVIDENCE</div>', unsafe_allow_html=True)
    st.title("Insights")
    st.markdown(
        '<div class="page-lead">날짜별 학습 기록과 Course 진도에서 분리된 Skill 숙련 근거를 확인한다.</div>',
        unsafe_allow_html=True,
    )
    summary = app.learning.study_summary()
    columns = st.columns(4)
    metrics = (
        (summary.completed_sessions, "완료 세션"),
        (f"{summary.completed_minutes:.0f}m", "학습 시간"),
        (summary.answered_questions, "풀이 문항"),
        (f"{summary.accuracy:.0%}", "정확도"),
    )
    for column, (value, label) in zip(columns, metrics):
        with column:
            st.markdown(
                f'<div class="metric-number">{value}</div><div class="metric-label">{label}</div>',
                unsafe_allow_html=True,
            )

    render_study_calendar(app)

    st.subheader("Weak Points")
    insights = app.learning.topic_insights()
    if not insights:
        st.info("Quiz를 풀면 topic별 정확도와 자신감이 여기에 쌓여.")
    for insight in insights:
        st.markdown(
            f'<div class="study-row"><div class="study-course">{html.escape(insight.course_id)} · '
            f'{html.escape(insight.skill_id)}</div><div class="study-title">{html.escape(insight.topic)}</div>'
            f'<div class="study-meta">정확도 {insight.accuracy:.0%} · 자신감 '
            f'{insight.average_confidence:.1f}/5 · 평균 {insight.average_response_seconds:.1f}초 · '
            f'취약도 {insight.weakness:.0%}</div></div>',
            unsafe_allow_html=True,
        )

    st.subheader("Skill Mastery")
    mastery = app.learning.skill_mastery()
    if not mastery:
        st.info("Course와 문항의 Skill metadata가 아직 없어.")
    for skill in mastery:
        st.markdown(
            f'<div class="course-row"><div class="study-course">SKILL</div>'
            f'<div class="study-title">{html.escape(skill.skill_id)}</div>'
            f'<div class="study-meta">{skill.score}% · {html.escape(skill.explanation)}</div>'
            f'<div class="progress-track"><div class="progress-fill" style="width:{skill.score}%"></div></div></div>',
            unsafe_allow_html=True,
        )


def _shift_month(month: date, offset: int) -> date:
    absolute_month = month.year * 12 + month.month - 1 + offset
    year, zero_based_month = divmod(absolute_month, 12)
    return date(year, zero_based_month + 1, 1)


def _calendar_month() -> date:
    current_month = date.today().replace(day=1)
    raw_value = st.session_state.get("insights-calendar-month")
    if isinstance(raw_value, str):
        try:
            selected = date.fromisoformat(f"{raw_value}-01")
        except ValueError:
            selected = current_month
    else:
        selected = current_month
    return min(selected, current_month)


def _activity_minutes(value: float) -> str:
    if value <= 0:
        return "시간 미기록"
    if value < 1:
        return "1분 미만"
    return f"{round(value)}분"


def _select_calendar_month(month: date) -> None:
    st.session_state["insights-calendar-month"] = month.strftime("%Y-%m")
    st.session_state.pop("insights-calendar-day", None)
    st.rerun()


def _render_calendar_day_details(
    app: LearningRuntime,
    selected_on: date,
    activities: list[StudyActivity],
) -> None:
    weekday = ("월", "화", "수", "목", "금", "토", "일")[selected_on.weekday()]
    st.markdown(f"#### {selected_on:%Y년 %m월 %d일} ({weekday})")

    lesson_activities = [item for item in activities if item.kind == "lesson"]
    quiz_activities = [item for item in activities if item.kind == "quiz"]
    with st.container(horizontal=True):
        st.metric("완료 Lesson", len(lesson_activities), border=True)
        st.metric("풀이 문항", len(quiz_activities), border=True)
        st.metric(
            "기록 시간",
            _activity_minutes(sum(item.duration_minutes for item in activities)),
            border=True,
        )

    for activity in lesson_activities:
        course = app.course(activity.course_id)
        lesson = app.lesson(activity.course_id, activity.lesson_id or "")
        course_title = course.title if course else activity.course_id
        lesson_title = lesson.title if lesson else (activity.lesson_id or "알 수 없는 Lesson")
        with st.container(border=True):
            st.caption(f"Lesson 완료 · {course_title}")
            st.markdown(f"**{lesson_title}**")
            expected = f" · 예상 {lesson.duration_minutes}분" if lesson else ""
            st.caption(
                f"완료 {activity.occurred_at:%H:%M} · 실제 기록 "
                f"{_activity_minutes(activity.duration_minutes)}{expected}"
            )
            if lesson and st.button(
                "Lesson 다시 보기",
                key=f"calendar-lesson:{selected_on}:{activity.course_id}:{lesson.id}",
                icon=":material/menu_book:",
            ):
                go("lesson", course_id=activity.course_id, lesson_id=lesson.id)

    quizzes_by_course: dict[str, list[StudyActivity]] = defaultdict(list)
    for activity in quiz_activities:
        quizzes_by_course[activity.course_id].append(activity)
    for course_id, items in quizzes_by_course.items():
        course = app.course(course_id)
        course_title = course.title if course else course_id
        correct = sum(item.correct is True for item in items)
        topics = ", ".join(dict.fromkeys(item.topic for item in items if item.topic))
        with st.container(border=True):
            st.caption(f"문제 풀이 · {course_title}")
            st.markdown(f"**{len(items)}문항 · {correct}/{len(items)} 정답**")
            st.caption(
                f"마지막 풀이 {items[-1].occurred_at:%H:%M} · 응답 시간 "
                f"{_activity_minutes(sum(item.duration_minutes for item in items))}"
            )
            if topics:
                st.caption(f"Topic · {topics}")


def render_study_calendar(app: LearningRuntime) -> None:
    st.subheader("학습 캘린더")
    st.caption("Lesson 완료와 문제 풀이를 로컬 날짜 기준으로 모아 보여줘.")
    selected_month = _calendar_month()
    current_month = date.today().replace(day=1)

    previous, month_title, following = st.columns(
        [1, 4, 1],
        vertical_alignment="center",
    )
    if previous.button(
        "이전 달",
        icon=":material/chevron_left:",
        width="stretch",
        key="calendar-previous-month",
    ):
        _select_calendar_month(_shift_month(selected_month, -1))
    month_title.markdown(
        f"### {selected_month:%Y년 %m월}",
        text_alignment="center",
    )
    if following.button(
        "다음 달",
        icon=":material/chevron_right:",
        width="stretch",
        disabled=selected_month >= current_month,
        key="calendar-next-month",
    ):
        _select_calendar_month(_shift_month(selected_month, 1))

    month_end = date(
        selected_month.year,
        selected_month.month,
        calendar.monthrange(selected_month.year, selected_month.month)[1],
    )
    activities = app.learning.study_activity(selected_month, month_end)
    activities_by_day: dict[date, list[StudyActivity]] = defaultdict(list)
    for activity in activities:
        activities_by_day[activity.occurred_at.date()].append(activity)

    lesson_count = sum(item.kind == "lesson" for item in activities)
    question_count = sum(item.kind == "quiz" for item in activities)
    with st.container(horizontal=True):
        st.metric("학습한 날", len(activities_by_day), border=True)
        st.metric("완료 Lesson", lesson_count, border=True)
        st.metric("풀이 문항", question_count, border=True)
        st.metric(
            "기록 시간",
            _activity_minutes(sum(item.duration_minutes for item in activities)),
            border=True,
        )

    weekday_columns = st.columns(7, gap="xsmall", wrap=False)
    for column, label in zip(weekday_columns, ("월", "화", "수", "목", "금", "토", "일")):
        column.markdown(f"**{label}**", text_alignment="center")

    selected_raw = st.session_state.get("insights-calendar-day")
    try:
        selected_on = date.fromisoformat(str(selected_raw))
    except ValueError:
        selected_on = max(activities_by_day, default=None)
    if selected_on not in activities_by_day:
        selected_on = max(activities_by_day, default=None)

    for week in calendar.Calendar(firstweekday=0).monthdatescalendar(
        selected_month.year,
        selected_month.month,
    ):
        day_columns = st.columns(7, gap="xsmall", wrap=False)
        for column, day in zip(day_columns, week):
            if day.month != selected_month.month:
                column.markdown("&nbsp;")
                continue
            day_activities = activities_by_day.get(day, [])
            day_lessons = sum(item.kind == "lesson" for item in day_activities)
            day_questions = sum(item.kind == "quiz" for item in day_activities)
            activity_parts = []
            if day_lessons:
                activity_parts.append(f"{day_lessons}강")
            if day_questions:
                activity_parts.append(f"{day_questions}문")
            marker = " · ".join(activity_parts) or ("오늘" if day == date.today() else "—")
            if column.button(
                f"**{day.day}**  \n{marker}",
                key=f"calendar-day:{day.isoformat()}",
                type="primary" if day == selected_on else "secondary",
                width="stretch",
                disabled=not day_activities,
                help=(
                    f"완료 Lesson {day_lessons}개 · 풀이 {day_questions}문항 · "
                    f"{_activity_minutes(sum(item.duration_minutes for item in day_activities))}"
                    if day_activities
                    else "학습 기록 없음"
                ),
            ):
                st.session_state["insights-calendar-day"] = day.isoformat()
                st.rerun()

    if selected_month != current_month:
        if st.button("이번 달로 돌아가기", icon=":material/today:"):
            _select_calendar_month(current_month)

    if not activities:
        st.info("이 달에는 아직 완료한 Lesson이나 문제 풀이 기록이 없어.")
        return
    assert selected_on is not None
    _render_calendar_day_details(app, selected_on, activities_by_day[selected_on])


def settings_page(app: LearningRuntime) -> None:
    st.markdown('<div class="eyebrow">LOCAL CONTROL</div>', unsafe_allow_html=True)
    st.title("Settings")
    st.markdown(
        '<div class="page-lead">학습 기본값과 로컬 데이터를 직접 관리한다.</div>',
        unsafe_allow_html=True,
    )
    current_minutes = stored_study_minutes(app)
    current_languages = sorted(stored_languages(app))
    with st.form("learning-settings"):
        minutes = st.select_slider(
            "기본 학습 시간",
            options=[15, 30, 45, 60, 90, 120],
            value=current_minutes,
            format_func=lambda value: f"{value}분",
        )
        languages = st.multiselect(
            "콘텐츠 언어",
            options=["ko", "en"],
            default=[language for language in current_languages if language in {"ko", "en"}],
            format_func=lambda language: {"ko": "한국어", "en": "English"}[language],
        )
        if st.form_submit_button("설정 저장", type="primary"):
            app.learning.set_setting("default_study_minutes", minutes)
            app.learning.set_setting("content_languages", languages or ["ko", "en"])
            st.session_state.study_minutes = minutes
            st.success("설정을 저장했어.")

    st.subheader("AI Tutor")
    st.caption("AI Provider는 optional이야. API key가 없어도 Quiz, Review, Notes와 Scheduler는 모두 동작해.")

    st.subheader("Backup / Restore")
    backup_manager = BackupManager(app.settings.data_dir, app.settings.database_path)
    if st.button("지금 백업", key="create-backup"):
        try:
            archive = backup_manager.create_backup()
        except BackupError as exc:
            st.error(str(exc))
        else:
            st.success(f"백업을 만들었어: {archive.name}")
    archives = sorted(backup_manager.backups_dir.glob("*.zip"), reverse=True)
    if archives:
        selected_backup = st.selectbox(
            "복원할 백업",
            options=archives,
            format_func=lambda path: path.name,
        )
        try:
            backup_info = backup_manager.inspect(selected_backup)
        except BackupError as exc:
            st.error(str(exc))
        else:
            versions = ", ".join(str(version) for version in backup_info.schema_versions)
            st.caption(
                f"생성 {backup_info.created_at} · {backup_info.size_bytes / 1024:.1f}KB · schema {versions}"
            )
            confirm_restore = st.checkbox(
                "현재 DB를 safety backup한 뒤 선택한 백업으로 복원한다",
                key="confirm-restore",
            )
            if st.button("선택한 백업 복원", disabled=not confirm_restore):
                app.connection.close()
                try:
                    safety = backup_manager.restore(selected_backup)
                except BackupError as exc:
                    runtime.clear()
                    st.error(f"복원하지 못했어: {exc}")
                    if exc.safety_backup_path:
                        st.caption(f"Safety backup: {exc.safety_backup_path.name}")
                    st.rerun()
                else:
                    runtime.clear()
                    st.success(f"복원했어. Safety backup: {safety.name}")
                    st.rerun()
    else:
        st.caption("아직 생성된 백업이 없어.")

    st.subheader("Course Import")
    st.caption("URL, PDF 또는 Markdown을 Manifest Course로 가져온다. 원본 파일은 Course 폴더에만 저장돼.")
    importer = CourseImporter(app.settings.courses_dir)
    url_tab, file_tab = st.tabs(["URL", "PDF / Markdown"])
    with url_tab:
        with st.form("import-url"):
            url_id = st.text_input("Course ID", key="import-url-id", placeholder="my-course")
            url_title = st.text_input("제목", key="import-url-title")
            source_url = st.text_input("URL", key="import-url-value")
            url_language = st.selectbox("언어", ["ko", "en"], key="import-url-language")
            if st.form_submit_button("URL Course 가져오기"):
                try:
                    importer.import_url(
                        course_id=url_id,
                        title=url_title,
                        url=source_url,
                        language=url_language,
                    )
                except CourseImportError as exc:
                    st.error(str(exc))
                else:
                    runtime.clear()
                    st.success("Course를 추가했어.")
                    st.rerun()
    with file_tab:
        with st.form("import-file"):
            file_id = st.text_input("Course ID", key="import-file-id", placeholder="my-document")
            file_title = st.text_input("제목", key="import-file-title")
            uploaded = st.file_uploader("파일", type=["pdf", "md", "markdown"])
            file_language = st.selectbox("언어", ["ko", "en"], key="import-file-language")
            if st.form_submit_button("파일 Course 가져오기"):
                if uploaded is None:
                    st.error("파일을 선택해라.")
                else:
                    try:
                        importer.import_document(
                            course_id=file_id,
                            title=file_title,
                            filename=uploaded.name,
                            content=uploaded.getvalue(),
                            language=file_language,
                        )
                    except CourseImportError as exc:
                        st.error(str(exc))
                    else:
                        runtime.clear()
                        st.success("Course를 추가했어.")
                        st.rerun()


def sidebar() -> str:
    target = st.session_state.pop("_navigation_target", None)
    destinations = ["dashboard", "courses", "review", "notes", "insights", "settings"]
    labels = {
        "dashboard": "오늘의 학습",
        "courses": "Courses",
        "review": "복습",
        "notes": "Notes",
        "insights": "Insights",
        "settings": "Settings",
    }
    if target in destinations:
        st.session_state.navigation = target

    def navigate() -> None:
        st.session_state.page = st.session_state.navigation

    with st.sidebar:
        st.markdown("## ◒ Learning OS")
        st.caption("Study first. Build second.")
        st.divider()
        selected = st.radio(
            "이동",
            destinations,
            format_func=lambda item: labels[item],
            label_visibility="collapsed",
            key="navigation",
            on_change=navigate,
        )
        st.divider()
        st.caption("Phase 2 · Local-first")
    if st.session_state.get("page") in {"course", "lesson", "practice"}:
        return str(st.session_state.page)
    return selected


def main() -> None:
    try:
        app = runtime()
    except Exception as exc:
        st.error("Learning OS를 시작하지 못했어.")
        st.exception(exc)
        st.stop()

    page = sidebar()
    if page == "dashboard":
        dashboard(app)
    elif page == "courses":
        courses_page(app)
    elif page == "review":
        review_page(app)
    elif page == "notes":
        notes_page(app)
    elif page == "insights":
        insights_page(app)
    elif page == "settings":
        settings_page(app)
    elif page == "course":
        course = app.course(str(st.session_state.get("course_id", "")))
        if course is None:
            st.error("Course를 찾을 수 없어.")
        else:
            course_page(app, course)
    elif page == "lesson":
        course_id = str(st.session_state.get("course_id", ""))
        lesson_id = str(st.session_state.get("lesson_id", ""))
        course = app.course(course_id)
        lesson = app.lesson(course_id, lesson_id)
        if course is None or lesson is None:
            st.error("Lesson을 찾을 수 없어.")
        else:
            lesson_page(app, course, lesson)
    elif page == "practice":
        practice_page(app)


if __name__ == "__main__":
    main()
