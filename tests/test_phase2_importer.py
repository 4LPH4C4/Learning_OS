from pathlib import Path

import pytest

from learning_os.core.manifests import load_manifest
from learning_os.integrations.course_importer import CourseImporter, CourseImportError


def test_url_import_creates_loadable_manifest(tmp_path: Path) -> None:
    importer = CourseImporter(tmp_path / "courses")

    imported = importer.import_url(
        course_id="systems-thinking",
        title="Systems Thinking",
        url="https://example.com/course",
        language="en",
    )
    course = load_manifest(imported.manifest_path)

    assert course.id == "systems-thinking"
    assert course.lessons[0].type == "url"
    assert course.lessons[0].url == "https://example.com/course"
    assert course.lessons[0].language == "en"


def test_pdf_import_stays_inside_course_and_rejects_duplicate(tmp_path: Path) -> None:
    importer = CourseImporter(tmp_path / "courses")
    imported = importer.import_document(
        course_id="local-paper",
        title="Local Paper",
        filename="paper.pdf",
        content=b"%PDF-1.4 test",
    )
    course = load_manifest(imported.manifest_path)

    assert (imported.root_path / "materials" / "source.pdf").read_bytes().startswith(b"%PDF")
    assert course.lessons[0].content_path == "materials/source.pdf"
    with pytest.raises(CourseImportError, match="이미 존재"):
        importer.import_url(
            course_id="local-paper",
            title="Duplicate",
            url="https://example.com",
        )


def test_import_falls_back_when_windows_blocks_directory_replace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    courses_dir = tmp_path / "courses"
    importer = CourseImporter(courses_dir)
    original_replace = Path.replace

    def blocked_replace(path: Path, target: Path) -> Path:
        if path.parent == courses_dir and path.name.startswith(".windows-lock-"):
            raise PermissionError("simulated Windows directory lock")
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", blocked_replace)
    imported = importer.import_url(
        course_id="windows-lock",
        title="Windows Lock",
        url="https://example.com/windows",
    )

    assert imported.manifest_path.exists()
    assert load_manifest(imported.manifest_path).id == "windows-lock"


@pytest.mark.parametrize("course_id", ["../escape", "Bad ID", "UPPER"])
def test_import_rejects_unsafe_course_id(tmp_path: Path, course_id: str) -> None:
    importer = CourseImporter(tmp_path / "courses")

    with pytest.raises(CourseImportError, match="kebab-case"):
        importer.import_url(course_id=course_id, title="Unsafe", url="https://example.com")
