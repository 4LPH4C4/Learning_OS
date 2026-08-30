from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from learning_os.config import Settings, load_settings
from learning_os.core.catalog import discover_courses
from learning_os.core.assessment import ReviewQuestion
from learning_os.core.models import Course, CourseCatalog, Lesson
from learning_os.core.question_bank import QuestionCatalog, discover_questions
from learning_os.database.connection import connect
from learning_os.database.learning_repository import LearningRepository
from learning_os.database.migrations import apply_migrations
from learning_os.database.progress_repository import ProgressRepository


@dataclass
class LearningRuntime:
    settings: Settings
    connection: sqlite3.Connection
    catalog: CourseCatalog
    questions: QuestionCatalog
    progress: ProgressRepository
    learning: LearningRepository

    def course(self, course_id: str) -> Course | None:
        return self.catalog.get(course_id)

    def lesson(self, course_id: str, lesson_id: str) -> Lesson | None:
        course = self.course(course_id)
        if course is None:
            return None
        return next((item for item in course.lessons if item.id == lesson_id), None)

    def due_reviews(self) -> tuple[ReviewQuestion, ...]:
        items = []
        for schedule in self.learning.due_schedules():
            question = self.questions.get(schedule.course_id, schedule.question_id)
            if question is not None:
                items.append(ReviewQuestion(question=question, schedule=schedule))
        return tuple(items)


def build_runtime(settings: Settings | None = None) -> LearningRuntime:
    settings = settings or load_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.external_dir.mkdir(parents=True, exist_ok=True)
    connection = connect(settings.database_path)
    apply_migrations(connection, settings.migrations_dir)
    catalog = discover_courses(settings.courses_dir)
    questions = discover_questions(catalog.courses)
    progress = ProgressRepository(connection)
    learning = LearningRepository(connection)
    progress.register_courses(catalog.courses)
    learning.sync_catalog(catalog.courses, questions.questions)
    return LearningRuntime(
        settings=settings,
        connection=connection,
        catalog=catalog,
        questions=questions,
        progress=progress,
        learning=learning,
    )
