from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Literal


CourseStatus = Literal["active", "planned", "disabled"]


@dataclass(frozen=True)
class CourseSchedule:
    start_date: date | None = None
    target_date: date | None = None
    exam_date: date | None = None
    estimated_hours: float | None = None
    weekly_target_hours: float | None = None
    priority: int = 0


@dataclass(frozen=True)
class ContentSource:
    id: str
    type: Literal["local", "github"]
    base_path: str | None = None
    repository_url: str | None = None
    branch: str | None = None
    sparse_paths: tuple[str, ...] = ()
    local_path: str | None = None


@dataclass(frozen=True)
class Lesson:
    id: str
    title: str
    type: str
    duration_minutes: int
    content_path: str | None = None
    notebook_path: str | None = None
    source_id: str | None = None
    required: bool = True
    skills: tuple[str, ...] = ()
    module_id: str = ""
    course_id: str = ""
    course_root: Path = Path()


@dataclass(frozen=True)
class Module:
    id: str
    title: str
    order: int
    lessons: tuple[Lesson, ...] = ()


@dataclass(frozen=True)
class CompletionCriteria:
    type: str = "all_required_lessons"
    value: Any = None


@dataclass(frozen=True)
class Course:
    schema_version: int
    id: str
    title: str
    description: str
    category: str
    source_type: str
    status: CourseStatus
    schedule: CourseSchedule
    prerequisites: tuple[str, ...]
    skills: tuple[str, ...]
    content_sources: tuple[ContentSource, ...]
    modules: tuple[Module, ...]
    completion_criteria: CompletionCriteria
    root_path: Path
    manifest_path: Path
    manifest_hash: str
    quiz_settings: dict[str, Any] | None = None

    @property
    def lessons(self) -> tuple[Lesson, ...]:
        return tuple(lesson for module in self.modules for lesson in module.lessons)

    @property
    def required_lessons(self) -> tuple[Lesson, ...]:
        return tuple(lesson for lesson in self.lessons if lesson.required)

    def source(self, source_id: str | None) -> ContentSource | None:
        if source_id is None:
            return None
        return next((source for source in self.content_sources if source.id == source_id), None)


@dataclass(frozen=True)
class CatalogIssue:
    manifest_path: Path
    message: str
    course_id: str | None = None


@dataclass(frozen=True)
class CourseCatalog:
    courses: tuple[Course, ...] = ()
    issues: tuple[CatalogIssue, ...] = ()

    def get(self, course_id: str) -> Course | None:
        return next((course for course in self.courses if course.id == course_id), None)


@dataclass(frozen=True)
class StudyRecommendation:
    course: Course
    lesson: Lesson
    reason: str


@dataclass(frozen=True)
class SourceState:
    source_id: str
    course_id: str
    status: str
    local_path: Path
    repository_url: str | None = None
    commit_sha: str | None = None
    last_sync_at: str | None = None
    error_message: str | None = None
    available: bool = False
