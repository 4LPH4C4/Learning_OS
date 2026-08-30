from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml

from learning_os.core.assessment import QuizOption, QuizQuestion
from learning_os.core.models import Course


ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
QUESTION_TYPES = {"single_choice", "multiple_choice", "short_answer"}


class QuestionBankError(ValueError):
    pass


@dataclass(frozen=True)
class QuestionBankIssue:
    path: Path
    message: str
    course_id: str | None = None


@dataclass(frozen=True)
class QuestionCatalog:
    questions: tuple[QuizQuestion, ...] = ()
    issues: tuple[QuestionBankIssue, ...] = ()

    def for_course(self, course_id: str) -> tuple[QuizQuestion, ...]:
        return tuple(question for question in self.questions if question.course_id == course_id)

    def get(self, course_id: str, question_id: str) -> QuizQuestion | None:
        return next(
            (
                question
                for question in self.questions
                if question.course_id == course_id and question.id == question_id
            ),
            None,
        )


def _mapping(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise QuestionBankError(f"{context}: mapping이어야 한다")
    return value


def _list(value: Any, context: str) -> list[Any]:
    if not isinstance(value, list):
        raise QuestionBankError(f"{context}: list여야 한다")
    return value


def _required(mapping: dict[str, Any], key: str, context: str) -> Any:
    value = mapping.get(key)
    if value is None or value == "":
        raise QuestionBankError(f"{context}.{key}: 필수 값이 없다")
    return value


def _id(value: Any, context: str) -> str:
    result = str(value)
    if not ID_PATTERN.fullmatch(result):
        raise QuestionBankError(f"{context}: 소문자 kebab-case ID가 필요하다")
    return result


def _question(raw: Any, course: Course, context: str) -> QuizQuestion:
    data = _mapping(raw, context)
    question_id = _id(_required(data, "id", context), f"{context}.id")
    skill_id = _id(_required(data, "skill_id", context), f"{context}.skill_id")
    question_type = str(_required(data, "type", context))
    if question_type not in QUESTION_TYPES:
        raise QuestionBankError(f"{context}.type: 지원하지 않는 문항 형식이다")
    try:
        difficulty = int(_required(data, "difficulty", context))
    except (TypeError, ValueError) as exc:
        raise QuestionBankError(f"{context}.difficulty: 1~5 정수가 필요하다") from exc
    if not 1 <= difficulty <= 5:
        raise QuestionBankError(f"{context}.difficulty: 1~5 범위여야 한다")

    lesson_id = str(data["lesson_id"]) if data.get("lesson_id") else None
    if lesson_id and not any(lesson.id == lesson_id for lesson in course.lessons):
        raise QuestionBankError(f"{context}.lesson_id: Course에 없는 Lesson이다")

    options = tuple(
        QuizOption(
            id=_id(_required(_mapping(item, f"{context}.options[{index}]"), "id", f"{context}.options[{index}]"), f"{context}.options[{index}].id"),
            text=str(_required(_mapping(item, f"{context}.options[{index}]"), "text", f"{context}.options[{index}]")),
        )
        for index, item in enumerate(_list(data.get("options", []), f"{context}.options"))
    )
    if question_type != "short_answer" and len(options) < 2:
        raise QuestionBankError(f"{context}.options: 선택형 문항에는 두 개 이상이 필요하다")
    option_ids = {option.id for option in options}
    if len(option_ids) != len(options):
        raise QuestionBankError(f"{context}.options: option ID가 중복됐다")

    answers = tuple(
        str(answer).strip()
        for answer in _list(_required(data, "correct_answers", context), f"{context}.correct_answers")
        if str(answer).strip()
    )
    if not answers:
        raise QuestionBankError(f"{context}.correct_answers: 정답이 필요하다")
    if question_type != "short_answer" and not set(answers).issubset(option_ids):
        raise QuestionBankError(f"{context}.correct_answers: 존재하지 않는 option이 있다")
    if question_type == "single_choice" and len(set(answers)) != 1:
        raise QuestionBankError(f"{context}.correct_answers: single_choice는 정답 하나가 필요하다")

    incorrect_raw = _mapping(data.get("incorrect_explanations", {}), f"{context}.incorrect_explanations")
    canonical = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return QuizQuestion(
        id=question_id,
        course_id=course.id,
        lesson_id=lesson_id,
        skill_id=skill_id,
        topic=str(_required(data, "topic", context)),
        difficulty=difficulty,
        type=question_type,  # type: ignore[arg-type]
        prompt=str(_required(data, "prompt", context)),
        options=options,
        correct_answers=answers,
        explanation=str(_required(data, "explanation", context)),
        incorrect_explanations=tuple(
            (str(key), str(value)) for key, value in incorrect_raw.items()
        ),
        source_ref=str(data["source_ref"]) if data.get("source_ref") else None,
        content_hash=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    )


def load_question_file(course: Course, path: Path | None = None) -> tuple[QuizQuestion, ...]:
    path = (path or course.root_path / "questions.yaml").resolve()
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise QuestionBankError(f"문항 파일을 읽을 수 없다: {exc}") from exc
    data = _mapping(data, "question_bank")
    try:
        schema_version = int(_required(data, "schema_version", "question_bank"))
    except (TypeError, ValueError) as exc:
        raise QuestionBankError("question_bank.schema_version: 정수가 필요하다") from exc
    if schema_version != 1:
        raise QuestionBankError(f"question_bank.schema_version: 지원하지 않는 버전 {schema_version}")
    if str(_required(data, "course_id", "question_bank")) != course.id:
        raise QuestionBankError("question_bank.course_id: Manifest Course ID와 다르다")
    questions = tuple(
        _question(raw, course, f"question_bank.questions[{index}]")
        for index, raw in enumerate(_list(data.get("questions", []), "question_bank.questions"))
    )
    ids = [question.id for question in questions]
    if len(ids) != len(set(ids)):
        raise QuestionBankError("question_bank.questions: question ID가 중복됐다")
    return questions


def discover_questions(courses: Iterable[Course]) -> QuestionCatalog:
    questions: list[QuizQuestion] = []
    issues: list[QuestionBankIssue] = []
    for course in courses:
        path = course.root_path / "questions.yaml"
        if not path.is_file():
            continue
        try:
            questions.extend(load_question_file(course, path))
        except QuestionBankError as exc:
            issues.append(QuestionBankIssue(path=path.resolve(), message=str(exc), course_id=course.id))
    return QuestionCatalog(
        questions=tuple(sorted(questions, key=lambda item: (item.course_id, item.topic, item.id))),
        issues=tuple(issues),
    )
