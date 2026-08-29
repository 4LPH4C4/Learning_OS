from __future__ import annotations

from pathlib import Path

from learning_os.core.manifests import ManifestError, load_manifest
from learning_os.core.models import CatalogIssue, CourseCatalog


def discover_courses(courses_dir: Path) -> CourseCatalog:
    courses = []
    issues = []
    if not courses_dir.exists():
        return CourseCatalog(issues=(CatalogIssue(courses_dir, "courses 폴더가 없다"),))

    for manifest_path in sorted(courses_dir.glob("*/course.yaml")):
        try:
            courses.append(load_manifest(manifest_path))
        except ManifestError as exc:
            issues.append(CatalogIssue(manifest_path=manifest_path, message=str(exc)))

    course_ids: set[str] = set()
    unique_courses = []
    for course in courses:
        if course.id in course_ids:
            issues.append(
                CatalogIssue(
                    manifest_path=course.manifest_path,
                    course_id=course.id,
                    message=f"Course ID '{course.id}'가 중복됐다",
                )
            )
            continue
        course_ids.add(course.id)
        unique_courses.append(course)
    return CourseCatalog(courses=tuple(unique_courses), issues=tuple(issues))
