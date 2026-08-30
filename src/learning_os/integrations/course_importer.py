from __future__ import annotations

import re
import shutil
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import yaml


ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class CourseImportError(RuntimeError):
    pass


@dataclass(frozen=True)
class ImportedCourse:
    course_id: str
    root_path: Path
    manifest_path: Path


class CourseImporter:
    def __init__(self, courses_dir: Path):
        self.courses_dir = courses_dir.resolve()

    def _target(self, course_id: str) -> Path:
        if not ID_PATTERN.fullmatch(course_id):
            raise CourseImportError("Course ID는 소문자 kebab-case여야 한다")
        target = (self.courses_dir / course_id).resolve()
        try:
            target.relative_to(self.courses_dir)
        except ValueError as exc:
            raise CourseImportError("Course 폴더 밖 경로는 사용할 수 없다") from exc
        if target.exists():
            raise CourseImportError(f"'{course_id}' Course가 이미 존재한다")
        return target

    @staticmethod
    def _base_manifest(course_id: str, title: str, language: str) -> dict[str, object]:
        if not title.strip():
            raise CourseImportError("Course 제목이 필요하다")
        if language not in {"ko", "en"}:
            raise CourseImportError("지원 언어는 ko 또는 en이다")
        return {
            "schema_version": 1,
            "id": course_id,
            "title": title.strip(),
            "description": "사용자가 가져온 학습 자료",
            "category": "imported",
            "source_type": "local",
            "status": "active",
            "schedule": {"priority": 10},
            "prerequisites": [],
            "skills": [],
            "content_sources": [{"id": "local-content", "type": "local", "base_path": "."}],
            "completion_criteria": {"type": "all_required_lessons"},
        }

    def _commit(self, course_id: str, target: Path, manifest: dict[str, object], files: dict[str, bytes]) -> ImportedCourse:
        self.courses_dir.mkdir(parents=True, exist_ok=True)
        temporary = Path(tempfile.mkdtemp(prefix=f".{course_id}-", dir=self.courses_dir))
        target_created = False
        try:
            for relative, content in files.items():
                destination = temporary / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(content)
            (temporary / "course.yaml").write_text(
                yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            for attempt in range(4):
                try:
                    temporary.replace(target)
                    break
                except PermissionError:
                    if attempt == 3:
                        # Windows 백신/인덱서가 임시 폴더 핸들을 잠시 잡는 경우를 대비한다.
                        # manifest를 마지막에 복사해 불완전한 Course가 탐색되지 않게 한다.
                        target.mkdir()
                        target_created = True
                        for child in temporary.iterdir():
                            if child.name == "course.yaml":
                                continue
                            destination = target / child.name
                            if child.is_dir():
                                shutil.copytree(child, destination)
                            else:
                                shutil.copy2(child, destination)
                        shutil.copy2(temporary / "course.yaml", target / "course.yaml")
                        shutil.rmtree(temporary)
                        break
                    time.sleep(0.05 * (attempt + 1))
        except (OSError, yaml.YAMLError) as exc:
            shutil.rmtree(temporary, ignore_errors=True)
            if target_created:
                shutil.rmtree(target, ignore_errors=True)
            raise CourseImportError(f"Course를 저장하지 못했다: {exc}") from exc
        return ImportedCourse(course_id=course_id, root_path=target, manifest_path=target / "course.yaml")

    def import_url(self, *, course_id: str, title: str, url: str, language: str = "ko") -> ImportedCourse:
        target = self._target(course_id)
        parsed = urlparse(url.strip())
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise CourseImportError("HTTP(S) URL이 필요하다")
        manifest = self._base_manifest(course_id, title, language)
        manifest["modules"] = [
            {
                "id": "imported-material",
                "title": "가져온 자료",
                "order": 1,
                "lessons": [
                    {
                        "id": "source-link",
                        "title": title.strip(),
                        "type": "url",
                        "duration_minutes": 30,
                        "url": url.strip(),
                        "language": language,
                        "required": True,
                        "skills": [],
                    }
                ],
            }
        ]
        return self._commit(course_id, target, manifest, {})

    def import_document(
        self,
        *,
        course_id: str,
        title: str,
        filename: str,
        content: bytes,
        language: str = "ko",
    ) -> ImportedCourse:
        target = self._target(course_id)
        suffix = Path(filename).suffix.casefold()
        if suffix not in {".pdf", ".md", ".markdown"}:
            raise CourseImportError("현재 PDF와 Markdown 파일만 가져올 수 있다")
        if not content:
            raise CourseImportError("빈 파일은 가져올 수 없다")
        safe_name = "source.pdf" if suffix == ".pdf" else "source.md"
        lesson_type = "pdf" if suffix == ".pdf" else "markdown"
        manifest = self._base_manifest(course_id, title, language)
        manifest["modules"] = [
            {
                "id": "imported-material",
                "title": "가져온 자료",
                "order": 1,
                "lessons": [
                    {
                        "id": "source-document",
                        "title": title.strip(),
                        "type": lesson_type,
                        "duration_minutes": 30,
                        "content_path": f"materials/{safe_name}",
                        "language": language,
                        "required": True,
                        "skills": [],
                    }
                ],
            }
        ]
        return self._commit(
            course_id,
            target,
            manifest,
            {f"materials/{safe_name}": content},
        )
