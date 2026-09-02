from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlparse

import yaml

from learning_os.core.models import Course


class GlossaryError(ValueError):
    pass


@dataclass(frozen=True)
class GlossaryTerm:
    id: str
    name: str
    aliases: tuple[str, ...]
    short_definition: str
    explanation: str
    example: str | None = None
    related_terms: tuple[str, ...] = ()
    source_url: str | None = None

    @property
    def search_text(self) -> str:
        return " ".join(
            (self.name, *self.aliases, self.short_definition, self.explanation, self.example or "")
        ).casefold()


@dataclass(frozen=True)
class CourseGlossary:
    course_id: str
    terms: tuple[GlossaryTerm, ...] = ()

    def get(self, term_id: str) -> GlossaryTerm | None:
        return next((term for term in self.terms if term.id == term_id), None)

    def search(self, query: str) -> tuple[GlossaryTerm, ...]:
        normalized = query.strip().casefold()
        if not normalized:
            return self.terms
        return tuple(term for term in self.terms if normalized in term.search_text)


def _strings(value: Any, context: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise GlossaryError(f"{context}: 문자열 목록이어야 한다")
    return tuple(item.strip() for item in value if item.strip())


def glossary_file(course: Course) -> Path | None:
    relative = course.glossary_path
    if relative:
        return (course.root_path / relative).resolve()
    conventional = (course.root_path / "glossary.yaml").resolve()
    return conventional if conventional.exists() else None


def load_glossary(course: Course) -> CourseGlossary:
    path = glossary_file(course)
    if path is None:
        return CourseGlossary(course_id=course.id)
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise GlossaryError(f"용어사전을 읽을 수 없다: {exc}") from exc
    if not isinstance(raw, dict):
        raise GlossaryError("용어사전 root는 mapping이어야 한다")
    if raw.get("version") != 1:
        raise GlossaryError("용어사전 version은 1이어야 한다")
    if str(raw.get("course_id", "")) != course.id:
        raise GlossaryError("용어사전 course_id가 Course와 다르다")
    raw_terms = raw.get("terms", [])
    if not isinstance(raw_terms, list):
        raise GlossaryError("terms는 목록이어야 한다")

    terms: list[GlossaryTerm] = []
    seen: set[str] = set()
    for index, item in enumerate(raw_terms):
        context = f"terms[{index}]"
        if not isinstance(item, dict):
            raise GlossaryError(f"{context}: mapping이어야 한다")
        term_id = str(item.get("id", "")).strip()
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", term_id) or term_id in seen:
            raise GlossaryError(f"{context}.id: 비어 있거나 중복됐다")
        seen.add(term_id)
        source_url = str(item["source_url"]).strip() if item.get("source_url") else None
        if source_url and urlparse(source_url).scheme not in {"http", "https"}:
            raise GlossaryError(f"{context}.source_url: http(s) URL이어야 한다")
        name = str(item.get("name", "")).strip()
        short_definition = str(item.get("short_definition", "")).strip()
        explanation = str(item.get("explanation", "")).strip()
        if not name or not short_definition or not explanation:
            raise GlossaryError(f"{context}: name, short_definition, explanation이 필요하다")
        terms.append(
            GlossaryTerm(
                id=term_id,
                name=name,
                aliases=_strings(item.get("aliases", []), f"{context}.aliases"),
                short_definition=short_definition,
                explanation=explanation,
                example=(str(item["example"]).strip() if item.get("example") else None),
                related_terms=_strings(item.get("related_terms", []), f"{context}.related_terms"),
                source_url=source_url,
            )
        )
    unknown_related = {
        related
        for term in terms
        for related in term.related_terms
        if related not in seen
    }
    if unknown_related:
        raise GlossaryError(f"존재하지 않는 related_terms: {', '.join(sorted(unknown_related))}")
    return CourseGlossary(course_id=course.id, terms=tuple(terms))


def terms_in_content(
    glossary: CourseGlossary,
    content: str,
    *,
    limit: int = 8,
) -> tuple[GlossaryTerm, ...]:
    normalized = content.casefold()
    matches: list[tuple[int, GlossaryTerm]] = []
    for term in glossary.terms:
        candidates = (term.name, *term.aliases)
        positions = []
        for candidate in candidates:
            needle = candidate.strip().casefold()
            if len(needle) < 2:
                continue
            if re.fullmatch(r"[a-z0-9][a-z0-9 _-]*", needle):
                match = re.search(
                    rf"(?<![a-z0-9_]){re.escape(needle)}(?![a-z0-9_])",
                    normalized,
                )
                if match:
                    positions.append(match.start())
            else:
                position = normalized.find(needle)
                if position >= 0:
                    positions.append(position)
        if positions:
            matches.append((min(positions), term))
    matches.sort(key=lambda item: (item[0], item[1].name.casefold()))
    return tuple(term for _, term in matches[: max(0, limit)])
