from __future__ import annotations

import html
import sys
import time
from datetime import date
from pathlib import Path

import streamlit as st


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from learning_os.core.models import Course, Lesson, StudyRecommendation  # noqa: E402
from learning_os.core.assessment import QuizQuestion, evaluate_answer  # noqa: E402
from learning_os.core.practice import profile_for, score_percent, select_questions  # noqa: E402
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
from learning_os.services.learning_service import LearningRuntime, build_runtime  # noqa: E402
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
        "question_started": time.monotonic(),
        "practice_started": time.monotonic(),
        "duration_minutes": duration_minutes,
        "target_score": target_score,
    }
    st.session_state.practice_parent = parent
    st.session_state.pop("practice_feedback", None)
    go("practice")


def start_course_practice(
    app: LearningRuntime,
    course: Course,
    mode: str,
    *,
    parent: str = "courses",
) -> None:
    available = app.questions.for_course(course.id)
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
    due_reviews = app.due_reviews()
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f'<div class="metric-number">{completed_today}</div><div class="metric-label">완료 Lesson</div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="metric-number">{active_courses}</div><div class="metric-label">활성 Course</div>', unsafe_allow_html=True)
    with c3:
        st.markdown(
            f'<div class="metric-number">{len(due_reviews)}</div><div class="metric-label">복습 예정</div>',
            unsafe_allow_html=True,
        )

    if due_reviews:
        st.header("Today's Review")
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

    st.header("Today's Study")
    default_minutes = stored_study_minutes(app)
    available = st.segmented_control(
        "오늘 가능한 시간",
        options=[15, 30, 45, 60, 90, 120],
        default=st.session_state.get("study_minutes", default_minutes),
        format_func=lambda value: f"{value}분",
        key="study_minutes",
    )
    recommendations = build_curriculum_plan(
        app.catalog.courses,
        statuses,
        int(available or default_minutes),
        weakness_by_course=app.learning.weakness_by_course(),
        allowed_languages=stored_languages(app),
    )
    if recommendations:
        recommendation_map = {
            f"{item.course.id}:{item.lesson.id}": item for item in recommendations
        }
        selected_refs = st.multiselect(
            "오늘 계획 조정",
            options=list(recommendation_map),
            default=list(recommendation_map),
            format_func=lambda ref: (
                f"{recommendation_map[ref].course.title} · "
                f"{recommendation_map[ref].lesson.title}"
            ),
            key=f"daily-plan:{available}",
        )
        selected = tuple(recommendation_map[ref] for ref in selected_refs)
        if st.button("오늘 공부 시작", type="primary", use_container_width=True):
            if selected:
                first = selected[0]
                open_lesson(app, first.course, first.lesson)
            else:
                st.warning("오늘 계획에 Lesson을 하나 이상 선택해라.")
        for index, item in enumerate(selected):
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
        st.info("이 Course는 아직 준비 예정 상태야.")

    render_source_status(app, course)

    course_questions = app.questions.for_course(course.id)
    if course_questions:
        st.subheader("Practice")
        profile = profile_for(course, "mock_exam")
        st.caption(
            f"문항 은행 {len(course_questions)}개 · Mock 목표 {profile.target_score}%"
            + (f" · {profile.duration_minutes}분" if profile.duration_minutes else "")
        )
        quiz_col, mock_col = st.columns(2)
        with quiz_col:
            if st.button("빠른 Quiz", type="primary", use_container_width=True, key=f"quiz:{course.id}"):
                start_course_practice(app, course, "quiz")
        with mock_col:
            if st.button("Mock Exam", use_container_width=True, key=f"mock:{course.id}"):
                start_course_practice(app, course, "mock_exam")

    allowed_languages = stored_languages(app)
    for module in course.modules:
        st.header(module.title)
        visible_lessons = tuple(
            lesson
            for lesson in module.lessons
            if lesson.language is None or lesson.language in allowed_languages
        )
        if not visible_lessons:
            st.caption("선택한 콘텐츠 언어에 해당하는 Lesson이 없어.")
        for lesson in visible_lessons:
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
                if lesson.type in {"quiz", "practice", "mock_exam"}:
                    label = "연습 시작"
                else:
                    label = "열기"
                if st.button(label, key=f"lesson:{course.id}:{lesson.id}", use_container_width=True):
                    if lesson.type in {"quiz", "practice", "mock_exam"}:
                        lesson_questions = tuple(
                            question
                            for question in course_questions
                            if question.lesson_id in {None, lesson.id}
                        )
                        mode = "mock_exam" if lesson.type == "mock_exam" else "practice"
                        start_practice_flow(app, lesson_questions, mode=mode, parent="courses")
                        continue
                    open_lesson(app, course, lesson)


def lesson_page(app: LearningRuntime, course: Course, lesson: Lesson) -> None:
    if st.button(f"← {course.title}", key="back-course"):
        go("course", course_id=course.id)
    st.markdown(f'<div class="eyebrow">{html.escape(course.title)} · {lesson.duration_minutes} MIN</div>', unsafe_allow_html=True)
    st.title(lesson.title)
    status = app.progress.statuses().get((course.id, lesson.id))
    if status == "completed":
        st.success("완료한 Lesson이야. 언제든 다시 볼 수 있어.")

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
        if st.button("Lesson 완료", type="primary", use_container_width=True):
            app.progress.mark_completed(course.id, lesson.id)
            session_key = f"session:{course.id}:{lesson.id}"
            session_id = st.session_state.pop(session_key, None)
            if session_id is not None:
                app.progress.complete_session(int(session_id))
            st.success("진도를 저장했어.")
            st.rerun()


def practice_page(app: LearningRuntime) -> None:
    state = st.session_state.get("practice_state")
    if not isinstance(state, dict):
        st.error("진행 중인 연습을 찾을 수 없어.")
        if st.button("Review로 이동"):
            go("review")
        return

    refs = list(state.get("question_refs", []))
    position = int(state.get("position", 0))
    if state.get("completed") or position >= len(refs):
        total = len(refs)
        correct = int(state.get("correct", 0))
        score = score_percent(correct, total)
        target_score = int(state.get("target_score") or 0)
        st.markdown('<div class="eyebrow">PRACTICE COMPLETE</div>', unsafe_allow_html=True)
        st.title(f"{score}%")
        st.markdown(
            f'<div class="page-lead">{total}문항 중 {correct}문항을 맞혔어. '
            "오답과 낮은 자신감 문항은 복습 일정에 자동 반영됐어.</div>",
            unsafe_allow_html=True,
        )
        if target_score:
            if score >= target_score:
                st.success(f"목표 {target_score}%를 달성했어.")
            else:
                st.info(f"목표 {target_score}%까지 {target_score - score}%p 남았어.")
        if st.button("Review에서 다음 복습 확인", type="primary"):
            st.session_state.pop("practice_state", None)
            st.session_state.pop("practice_feedback", None)
            go("review")
        return

    course_id, question_id = refs[position]
    question = app.questions.get(str(course_id), str(question_id))
    if question is None:
        st.error("문항을 찾을 수 없어. questions.yaml을 다시 확인해라.")
        return

    mode_label = {
        "quiz": "Quick Quiz",
        "review": "Today's Review",
        "practice": "Practice",
        "mock_exam": "Mock Exam",
    }.get(str(state.get("mode")), "Practice")
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
    st.title("Review")
    st.markdown(
        '<div class="page-lead">오답과 자신감이 낮았던 내용을 정해진 간격으로 다시 확인한다.</div>',
        unsafe_allow_html=True,
    )
    due = app.due_reviews()
    if due:
        st.subheader(f"오늘 복습 {len(due)}문항")
        for item in due[:10]:
            st.markdown(
                f'<div class="study-row"><div class="study-course">{html.escape(item.question.course_id)}</div>'
                f'<div class="study-title">{html.escape(item.question.topic)}</div>'
                f'<div class="study-meta">마감 {item.schedule.due_on} · '
                f'{item.schedule.interval_days}일 간격 · 자신감 {item.schedule.last_confidence}/5</div></div>',
                unsafe_allow_html=True,
            )
        if st.button("Today's Review 시작", type="primary", use_container_width=True):
            start_practice_flow(
                app,
                tuple(item.question for item in due[:10]),
                mode="review",
                parent="review",
            )
    else:
        st.success("오늘 마감인 복습은 없어. 빠른 Quiz로 새 복습 주기를 만들 수 있어.")

    st.subheader("Quick Practice")
    for course in app.catalog.courses:
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
            if st.button("Quiz 시작", key=f"review-quiz:{course.id}", use_container_width=True):
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
        '<div class="page-lead">학습량과 Course 진도에서 분리된 Skill 숙련 근거를 확인한다.</div>',
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
        "dashboard": "오늘",
        "courses": "Courses",
        "review": "Review",
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
