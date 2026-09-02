from __future__ import annotations

import hashlib
import re
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

from learning_os.core.models import (
    CompletionCriteria,
    ContentSource,
    Course,
    CourseSchedule,
    Lesson,
    Module,
    StudyStep,
)


ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SUPPORTED_SOURCE_TYPES = {"local", "github"}
SUPPORTED_LESSON_TYPES = {
    "markdown",
    "notebook",
    "markdown_notebook",
    "external_markdown",
    "external_notebook",
    "quiz",
    "practice",
    "mock_exam",
    "url",
    "pdf",
    "vocabulary",
    "listening",
    "speaking",
}


class ManifestError(ValueError):
    pass


def _mapping(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ManifestError(f"{context}: mapping이어야 한다")
    return value


def _list(value: Any, context: str) -> list[Any]:
    if not isinstance(value, list):
        raise ManifestError(f"{context}: list여야 한다")
    return value


def _integer(value: Any, context: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ManifestError(f"{context}: 정수가 필요하다") from exc


def _number(value: Any, context: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ManifestError(f"{context}: 숫자가 필요하다") from exc


def _strings(value: Any, context: str) -> tuple[str, ...]:
    return tuple(str(item) for item in _list(value, context))


def _required(mapping: dict[str, Any], key: str, context: str) -> Any:
    value = mapping.get(key)
    if value is None or value == "":
        raise ManifestError(f"{context}.{key}: 필수 값이 없다")
    return value


def _id(value: Any, context: str) -> str:
    result = str(value)
    if not ID_PATTERN.fullmatch(result):
        raise ManifestError(f"{context}: 소문자 kebab-case ID가 필요하다")
    return result


def _date(value: Any, context: str) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise ManifestError(f"{context}: YYYY-MM-DD 날짜가 필요하다") from exc


def _safe_relative_path(value: Any, course_root: Path, context: str) -> str | None:
    if value in (None, ""):
        return None
    raw = Path(str(value))
    if raw.is_absolute():
        raise ManifestError(f"{context}: 절대 경로는 허용하지 않는다")
    resolved = (course_root / raw).resolve()
    try:
        resolved.relative_to(course_root.resolve())
    except ValueError as exc:
        raise ManifestError(f"{context}: Course 폴더 밖 경로는 허용하지 않는다") from exc
    return raw.as_posix()


def _safe_url(value: Any, context: str) -> str | None:
    if value in (None, ""):
        return None
    result = str(value).strip()
    parsed = urlparse(result)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ManifestError(f"{context}: HTTP(S) URL이 필요하다")
    return result


def _parse_source(raw: dict[str, Any], course_root: Path, context: str) -> ContentSource:
    raw = _mapping(raw, context)
    source_id = _id(_required(raw, "id", context), f"{context}.id")
    source_type = str(_required(raw, "type", context))
    if source_type not in SUPPORTED_SOURCE_TYPES:
        raise ManifestError(f"{context}.type: 지원하지 않는 source type '{source_type}'")
    base_path = _safe_relative_path(raw.get("base_path"), course_root, f"{context}.base_path")
    repository_url = raw.get("repository_url")
    if source_type == "github" and not repository_url:
        raise ManifestError(f"{context}.repository_url: GitHub source에 필수다")
    return ContentSource(
        id=source_id,
        type=source_type,  # type: ignore[arg-type]
        base_path=base_path,
        repository_url=str(repository_url) if repository_url else None,
        branch=str(raw["branch"]) if raw.get("branch") else None,
        sparse_paths=tuple(
            str(path).strip("/")
            for path in _list(raw.get("sparse_paths", []), f"{context}.sparse_paths")
        ),
        local_path=str(raw["local_path"]) if raw.get("local_path") else None,
    )


def _parse_lesson(
    raw: dict[str, Any],
    *,
    course_id: str,
    module_id: str,
    course_root: Path,
    context: str,
    source_ids: set[str],
) -> Lesson:
    raw = _mapping(raw, context)
    lesson_id = _id(_required(raw, "id", context), f"{context}.id")
    lesson_type = str(_required(raw, "type", context))
    if lesson_type not in SUPPORTED_LESSON_TYPES:
        raise ManifestError(f"{context}.type: 지원하지 않는 lesson type '{lesson_type}'")
    source_id = str(raw["source_id"]) if raw.get("source_id") else None
    if source_id and source_id not in source_ids:
        raise ManifestError(f"{context}.source_id: 존재하지 않는 source '{source_id}'")
    content_path = _safe_relative_path(raw.get("content_path"), course_root, f"{context}.content_path")
    notebook_path = _safe_relative_path(raw.get("notebook_path"), course_root, f"{context}.notebook_path")
    url = _safe_url(raw.get("url"), f"{context}.url")
    if lesson_type in {"markdown", "external_markdown", "markdown_notebook"} and not content_path:
        raise ManifestError(f"{context}.content_path: {lesson_type}에 필수다")
    if lesson_type in {"notebook", "external_notebook", "markdown_notebook"} and not notebook_path:
        raise ManifestError(f"{context}.notebook_path: {lesson_type}에 필수다")
    if lesson_type in {"pdf", "vocabulary", "listening", "speaking"} and not content_path:
        raise ManifestError(f"{context}.content_path: {lesson_type}에 필수다")
    if lesson_type == "url" and not url:
        raise ManifestError(f"{context}.url: url Lesson에 필수다")
    try:
        duration = int(_required(raw, "duration_minutes", context))
    except (TypeError, ValueError) as exc:
        raise ManifestError(f"{context}.duration_minutes: 정수가 필요하다") from exc
    if duration <= 0:
        raise ManifestError(f"{context}.duration_minutes: 1 이상이어야 한다")
    study_steps_raw = _list(raw.get("study_steps", []), f"{context}.study_steps")
    study_steps: list[StudyStep] = []
    for step_index, step_raw in enumerate(study_steps_raw):
        step_context = f"{context}.study_steps[{step_index}]"
        step_raw = _mapping(step_raw, step_context)
        step_duration = _integer(
            _required(step_raw, "duration_minutes", step_context),
            f"{step_context}.duration_minutes",
        )
        if step_duration <= 0:
            raise ManifestError(f"{step_context}.duration_minutes: 1 이상이어야 한다")
        study_steps.append(
            StudyStep(
                label=str(_required(step_raw, "label", step_context)),
                duration_minutes=step_duration,
                outcome=(str(step_raw["outcome"]) if step_raw.get("outcome") else None),
            )
        )
    if study_steps and sum(step.duration_minutes for step in study_steps) != duration:
        raise ManifestError(
            f"{context}.study_steps: 단계 시간 합계가 duration_minutes({duration})와 같아야 한다"
        )
    return Lesson(
        id=lesson_id,
        title=str(_required(raw, "title", context)),
        type=lesson_type,
        duration_minutes=duration,
        content_path=content_path,
        notebook_path=notebook_path,
        source_id=source_id,
        url=url,
        language=str(raw["language"]) if raw.get("language") else None,
        level=(
            _id(raw["level"], f"{context}.level")
            if raw.get("level")
            else None
        ),
        required=bool(raw.get("required", True)),
        skills=_strings(raw.get("skills", []), f"{context}.skills"),
        study_steps=tuple(study_steps),
        module_id=module_id,
        course_id=course_id,
        course_root=course_root,
    )


def load_manifest(manifest_path: Path) -> Course:
    manifest_path = manifest_path.resolve()
    course_root = manifest_path.parent
    try:
        raw_bytes = manifest_path.read_bytes()
        data = yaml.safe_load(raw_bytes) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise ManifestError(f"Manifest를 읽을 수 없다: {exc}") from exc
    if not isinstance(data, dict):
        raise ManifestError("Manifest root는 mapping이어야 한다")

    course_id = _id(_required(data, "id", "course"), "course.id")
    schema_version = _integer(_required(data, "schema_version", "course"), "course.schema_version")
    if schema_version != 1:
        raise ManifestError(f"course.schema_version: 지원하지 않는 버전 {schema_version}")
    status = str(data.get("status", "active"))
    if status not in {"active", "planned", "disabled"}:
        raise ManifestError("course.status: active, planned, disabled 중 하나여야 한다")

    source_type = str(_required(data, "source_type", "course"))
    if source_type not in SUPPORTED_SOURCE_TYPES:
        raise ManifestError(f"course.source_type: 지원하지 않는 type '{source_type}'")

    schedule_raw = _mapping(data.get("schedule") or {}, "course.schedule")
    schedule = CourseSchedule(
        start_date=_date(schedule_raw.get("start_date"), "course.schedule.start_date"),
        target_date=_date(schedule_raw.get("target_date"), "course.schedule.target_date"),
        exam_date=_date(schedule_raw.get("exam_date"), "course.schedule.exam_date"),
        estimated_hours=_number(schedule_raw["estimated_hours"], "course.schedule.estimated_hours") if schedule_raw.get("estimated_hours") is not None else None,
        weekly_target_hours=_number(schedule_raw["weekly_target_hours"], "course.schedule.weekly_target_hours") if schedule_raw.get("weekly_target_hours") is not None else None,
        priority=_integer(schedule_raw.get("priority", 0), "course.schedule.priority"),
    )

    sources_raw = _list(data.get("content_sources", []), "course.content_sources")
    sources = tuple(
        _parse_source(source, course_root, f"course.content_sources[{index}]")
        for index, source in enumerate(sources_raw)
    )
    source_ids = {source.id for source in sources}
    if len(source_ids) != len(sources):
        raise ManifestError("course.content_sources: source ID가 중복됐다")

    modules_raw = _list(data.get("modules", []), "course.modules")
    modules: list[Module] = []
    all_lesson_ids: set[str] = set()
    module_ids: set[str] = set()
    for module_index, module_raw in enumerate(modules_raw):
        context = f"course.modules[{module_index}]"
        module_raw = _mapping(module_raw, context)
        module_id = _id(_required(module_raw, "id", context), f"{context}.id")
        if module_id in module_ids:
            raise ManifestError(f"{context}.id: module ID가 중복됐다")
        module_ids.add(module_id)
        lessons_raw = _list(module_raw.get("lessons", []), f"{context}.lessons")
        lessons = tuple(
            _parse_lesson(
                lesson_raw,
                course_id=course_id,
                module_id=module_id,
                course_root=course_root,
                context=f"{context}.lessons[{lesson_index}]",
                source_ids=source_ids,
            )
            for lesson_index, lesson_raw in enumerate(lessons_raw)
        )
        for lesson in lessons:
            if lesson.id in all_lesson_ids:
                raise ManifestError(f"lesson ID '{lesson.id}'가 Course 안에서 중복됐다")
            all_lesson_ids.add(lesson.id)
        modules.append(
            Module(
                id=module_id,
                title=str(_required(module_raw, "title", context)),
                order=_integer(module_raw.get("order", module_index + 1), f"{context}.order"),
                lessons=lessons,
            )
        )

    completion_raw = _mapping(
        data.get("completion_criteria") or {"type": "all_required_lessons"},
        "course.completion_criteria",
    )
    glossary_path = _safe_relative_path(
        data.get("glossary_path"), course_root, "course.glossary_path"
    )

    course = Course(
        schema_version=schema_version,
        id=course_id,
        title=str(_required(data, "title", "course")),
        description=str(data.get("description", "")),
        category=str(_required(data, "category", "course")),
        source_type=source_type,
        status=status,  # type: ignore[arg-type]
        schedule=schedule,
        prerequisites=_strings(data.get("prerequisites", []), "course.prerequisites"),
        skills=_strings(data.get("skills", []), "course.skills"),
        content_sources=sources,
        modules=tuple(sorted(modules, key=lambda item: item.order)),
        completion_criteria=CompletionCriteria(
            type=str(completion_raw.get("type", "all_required_lessons")),
            value=completion_raw.get("value"),
        ),
        root_path=course_root,
        manifest_path=manifest_path,
        manifest_hash=hashlib.sha256(raw_bytes).hexdigest(),
        quiz_settings=(
            _mapping(data["quiz_settings"], "course.quiz_settings")
            if data.get("quiz_settings") is not None
            else None
        ),
        glossary_path=glossary_path,
    )
    try:
        from learning_os.core.adaptive import mock_exam_sets, placement_config

        placement_config(course)
        mock_exam_sets(course)
    except ValueError as exc:
        raise ManifestError(str(exc)) from exc
    return course
