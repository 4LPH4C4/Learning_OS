from __future__ import annotations

import html
import sys
from datetime import date
from pathlib import Path

import streamlit as st


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from learning_os.core.models import Course, Lesson, StudyRecommendation  # noqa: E402
from learning_os.core.today import build_today_plan  # noqa: E402
from learning_os.integrations.content_loader import (  # noqa: E402
    ContentUnavailableError,
    read_markdown,
    resolve_content_path,
    without_leading_title,
)
from learning_os.integrations.github_source import (  # noqa: E402
    GitHubSourceManager,
    SourceError,
)
from learning_os.integrations.notebook_launcher import (  # noqa: E402
    NotebookLaunchError,
    launch_notebook,
)
from learning_os.services.learning_service import LearningRuntime, build_runtime  # noqa: E402
from learning_os.ui.theme import apply_theme  # noqa: E402


st.set_page_config(page_title="Learning OS", page_icon="◒", layout="wide")
apply_theme()


@st.cache_resource
def runtime() -> LearningRuntime:
    return build_runtime()


def go(page: str, *, course_id: str | None = None, lesson_id: str | None = None) -> None:
    st.session_state.page = page
    st.session_state._navigation_target = page if page in {"dashboard", "courses"} else "courses"
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


def progress_percent(app: LearningRuntime, course: Course) -> tuple[int, int, int]:
    completed, total = app.progress.progress_for(course)
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


def render_recommendation(app: LearningRuntime, item: StudyRecommendation, index: int) -> None:
    left, right = st.columns([5, 1.35], vertical_alignment="center")
    with left:
        st.markdown(
            f"""
            <div class="study-row">
              <div class="study-course">{html.escape(item.course.title)}</div>
              <div class="study-title">{html.escape(item.lesson.title)}</div>
              <div class="study-meta">{item.lesson.duration_minutes}분 · {html.escape(item.reason)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        if st.button(
            "학습 시작",
            key=f"start:{item.course.id}:{item.lesson.id}:{index}",
            type="primary" if index == 0 else "secondary",
            use_container_width=True,
        ):
            open_lesson(app, item.course, item.lesson)


def dashboard(app: LearningRuntime) -> None:
    today_text = date.today().strftime("%Y.%m.%d")
    st.markdown(f'<div class="eyebrow">TODAY · {today_text}</div>', unsafe_allow_html=True)
    st.title("Learning OS")
    st.markdown(
        '<div class="page-lead">오늘 할 일을 고르는 시간을 줄이고, 한 Lesson씩 실제 역량을 쌓는다.</div>',
        unsafe_allow_html=True,
    )

    statuses = app.progress.statuses()
    completed_today = sum(1 for status in statuses.values() if status == "completed")
    active_courses = sum(1 for course in app.catalog.courses if course.status == "active")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f'<div class="metric-number">{completed_today}</div><div class="metric-label">완료 Lesson</div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="metric-number">{active_courses}</div><div class="metric-label">활성 Course</div>', unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="metric-number">60m</div><div class="metric-label">오늘 기본 시간</div>', unsafe_allow_html=True)

    st.header("Today's Study")
    available = st.segmented_control(
        "오늘 가능한 시간",
        options=[15, 30, 45, 60, 90, 120],
        default=st.session_state.get("study_minutes", 60),
        format_func=lambda value: f"{value}분",
        key="study_minutes",
    )
    recommendations = build_today_plan(app.catalog.courses, statuses, int(available or 60))
    if recommendations:
        if st.button("오늘 공부 시작", type="primary", use_container_width=True):
            first = recommendations[0]
            open_lesson(app, first.course, first.lesson)
        for index, item in enumerate(recommendations):
            render_recommendation(app, item, index)
    else:
        st.success("오늘 필요한 Lesson을 모두 완료했어. Course에서 다음 항목을 확인해도 좋아.")

    st.header("Course Progress")
    for course in app.catalog.courses:
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
    st.markdown('<div class="page-lead">Course와 콘텐츠는 Manifest로 연결되고, 진도는 별도로 안전하게 저장된다.</div>', unsafe_allow_html=True)
    for course in app.catalog.courses:
        left, right = st.columns([5, 1.25], vertical_alignment="center")
        with left:
            render_progress(app, course)
            st.caption(course.description)
        with right:
            if st.button("살펴보기", key=f"browse:{course.id}", use_container_width=True):
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
    if course.status == "planned":
        st.info("이 Course는 Phase 1에서 구조만 준비했다.")

    render_source_status(app, course)

    for module in course.modules:
        st.header(module.title)
        for lesson in module.lessons:
            status = app.progress.statuses().get((course.id, lesson.id))
            left, right = st.columns([5, 1.25], vertical_alignment="center")
            with left:
                marker = "완료" if status == "completed" else "다음 학습"
                st.markdown(
                    f'<div class="study-row"><div class="study-course">{html.escape(marker)}</div>'
                    f'<div class="study-title">{html.escape(lesson.title)}</div>'
                    f'<div class="study-meta">{lesson.duration_minutes}분 · {html.escape(lesson.type)}</div></div>',
                    unsafe_allow_html=True,
                )
            with right:
                if st.button("열기", key=f"lesson:{course.id}:{lesson.id}", use_container_width=True):
                    open_lesson(app, course, lesson)


def lesson_page(app: LearningRuntime, course: Course, lesson: Lesson) -> None:
    if st.button(f"← {course.title}", key="back-course"):
        go("course", course_id=course.id)
    st.markdown(f'<div class="eyebrow">{html.escape(course.title)} · {lesson.duration_minutes} MIN</div>', unsafe_allow_html=True)
    st.title(lesson.title)
    status = app.progress.statuses().get((course.id, lesson.id))
    if status == "completed":
        st.success("완료한 Lesson이야. 언제든 다시 볼 수 있어.")

    if lesson.content_path:
        try:
            content = read_markdown(course, lesson, app.settings.external_dir)
            st.markdown(without_leading_title(content))
        except ContentUnavailableError as exc:
            st.warning(str(exc))
            source = course.source(lesson.source_id)
            if source and source.type == "github":
                st.info("Course 화면에서 원본 source를 준비한 뒤 다시 열어라.")

    if lesson.notebook_path:
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

    st.divider()
    if status != "completed":
        if st.button("Lesson 완료", type="primary", use_container_width=True):
            app.progress.mark_completed(course.id, lesson.id)
            session_key = f"session:{course.id}:{lesson.id}"
            session_id = st.session_state.pop(session_key, None)
            if session_id is not None:
                app.progress.complete_session(int(session_id))
            st.success("진도를 저장했어.")
            st.rerun()


def sidebar() -> str:
    target = st.session_state.pop("_navigation_target", None)
    if target in {"dashboard", "courses"}:
        st.session_state.navigation = target

    def navigate() -> None:
        st.session_state.page = st.session_state.navigation

    with st.sidebar:
        st.markdown("## ◒ Learning OS")
        st.caption("Study first. Build second.")
        st.divider()
        selected = st.radio(
            "이동",
            ["dashboard", "courses"],
            format_func=lambda item: {"dashboard": "오늘", "courses": "Courses"}[item],
            label_visibility="collapsed",
            key="navigation",
            on_change=navigate,
        )
        st.divider()
        st.caption("Phase 1 · Local-first")
    if st.session_state.get("page") in {"course", "lesson"}:
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


if __name__ == "__main__":
    main()
