from __future__ import annotations

from pathlib import Path

from learning_os.core.models import Course, Lesson


class ContentUnavailableError(RuntimeError):
    pass


def _within(path: Path, root: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ContentUnavailableError(f"허용된 콘텐츠 폴더 밖의 경로다: {path}") from exc
    return resolved


def source_root(course: Course, lesson: Lesson, external_dir: Path) -> Path:
    source = course.source(lesson.source_id)
    if source is None and lesson.source_id is None and len(course.content_sources) == 1:
        source = course.content_sources[0]
    if source is None:
        return course.root_path
    if source.type == "local":
        if not source.base_path:
            return course.root_path
        return _within(course.root_path / source.base_path, course.root_path)
    if not source.local_path:
        raise ContentUnavailableError(f"'{source.id}' source의 local_path가 없다")
    return _within(external_dir / source.local_path, external_dir)


def resolve_content_path(
    course: Course,
    lesson: Lesson,
    external_dir: Path,
    *,
    notebook: bool = False,
) -> Path:
    relative = lesson.notebook_path if notebook else lesson.content_path
    if not relative:
        kind = "Notebook" if notebook else "Lesson"
        raise ContentUnavailableError(f"{kind} 경로가 Manifest에 없다")
    root = source_root(course, lesson, external_dir)
    path = _within(root / relative, root)
    if not path.is_file():
        raise ContentUnavailableError(f"콘텐츠 파일을 찾을 수 없다: {relative}")
    return path


def read_markdown(course: Course, lesson: Lesson, external_dir: Path) -> str:
    path = resolve_content_path(course, lesson, external_dir)
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ContentUnavailableError(f"UTF-8 Markdown이 아니다: {path.name}") from exc
    except OSError as exc:
        raise ContentUnavailableError(f"Lesson을 읽을 수 없다: {exc}") from exc


def without_leading_title(markdown: str) -> str:
    """Remove one document H1 because the app already renders the Lesson title."""
    lines = markdown.splitlines()
    for index, line in enumerate(lines):
        if not line.strip():
            continue
        if line.lstrip().startswith("# "):
            del lines[index]
            while index < len(lines) and not lines[index].strip():
                del lines[index]
        break
    return "\n".join(lines)
