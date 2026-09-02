from __future__ import annotations

from collections import Counter
from pathlib import Path

from learning_os.core.adaptive import (
    mock_exam_sets,
    personalize_course,
    placement_config,
    placement_result,
    recommend_placement,
)
from learning_os.core.catalog import discover_courses
from learning_os.core.practice import profile_for_set
from learning_os.core.question_bank import discover_questions


ROOT = Path(__file__).parents[1]


def _catalogs():
    courses = discover_courses(ROOT / "courses")
    assert courses.issues == ()
    questions = discover_questions(courses.courses)
    assert questions.issues == ()
    return courses, questions


def test_english_placement_opens_the_recommended_cefr_path() -> None:
    courses, questions = _catalogs()
    course = courses.get("english-cefr")
    assert course is not None
    config = placement_config(course)
    assert config is not None
    assert [level.id for level in config.levels] == ["a1", "a2", "b1", "b2", "c1", "c2"]
    assert config.question_count >= 36

    placement_questions = questions.for_set(course.id, config.question_set)
    assert len(placement_questions) >= config.question_count
    assert {question.level for question in placement_questions} == {
        "a1", "a2", "b1", "b2", "c1", "c2"
    }
    answer_positions = Counter(
        next(
            index
            for index, option in enumerate(question.options)
            if option.id in question.correct_answers
        )
        for question in placement_questions
    )
    assert answer_positions == {0: 9, 1: 9, 2: 9, 3: 9}

    before = personalize_course(course, None)
    assert [lesson.id for lesson in before.lessons] == [config.lesson_id]
    c1_score = next(level.min_score for level in config.levels if level.id == "c1")
    result = recommend_placement(
        course,
        score_percent=c1_score,
        correct_count=30,
        question_count=36,
    )
    path = personalize_course(course, result)
    assert result.level_id == "c1"
    assert {lesson.level for lesson in path.lessons if lesson.level} == {"c1", "c2"}

    sequential_result = recommend_placement(
        course,
        score_percent=33,
        correct_count=12,
        question_count=36,
        correct_by_level={level.id: 2 for level in config.levels},
        total_by_level={level.id: 6 for level in config.levels},
    )
    assert sequential_result.level_id == "a1"
    restored = placement_result(sequential_result.as_dict(), course)
    assert restored is not None
    assert restored.level_id == sequential_result.level_id
    assert restored.level_scores == sequential_result.level_scores


def test_chinese_placement_covers_beginner_through_hsk9() -> None:
    courses, questions = _catalogs()
    course = courses.get("chinese-hsk")
    assert course is not None
    config = placement_config(course)
    assert config is not None
    expected = ["beginner", *(f"hsk{level}" for level in range(1, 10))]
    assert [level.id for level in config.levels] == expected
    assert config.question_count >= 50

    placement_questions = questions.for_set(course.id, config.question_set)
    assert len(placement_questions) >= config.question_count
    assert {question.level for question in placement_questions} == set(expected)
    assert all(question.source_ref and "chinesetest.cn" in question.source_ref for question in placement_questions)
    answer_positions = Counter(
        next(
            index
            for index, option in enumerate(question.options)
            if option.id in question.correct_answers
        )
        for question in placement_questions
    )
    assert sorted(answer_positions.values()) == [12, 12, 13, 13]


def test_ncs_has_ten_fixed_fifty_question_comprehensive_mocks() -> None:
    courses, questions = _catalogs()
    course = courses.get("ncs-core")
    assert course is not None
    exam_sets = mock_exam_sets(course)
    assert [item.id for item in exam_sets] == [f"round-{index:02d}" for index in range(1, 11)]
    assert all(profile_for_set(item).question_count == 50 for item in exam_sets)
    assert all(profile_for_set(item).duration_minutes == 60 for item in exam_sets)

    question_ids: set[str] = set()
    for exam_set in exam_sets:
        round_questions = questions.for_set(course.id, exam_set.id)
        assert len(round_questions) == 50
        assert len({question.skill_id for question in round_questions}) == 7
        assert all(question.source_ref and "ncs.go.kr" in question.source_ref for question in round_questions)
        answer_positions = Counter(
            next(
                index
                for index, option in enumerate(question.options)
                if option.id in question.correct_answers
            )
            for question in round_questions
        )
        assert max(answer_positions.values()) - min(answer_positions.values()) <= 6
        assert sum(question.difficulty >= 4 for question in round_questions) >= 5
        assert question_ids.isdisjoint(question.id for question in round_questions)
        question_ids.update(question.id for question in round_questions)
    assert len(question_ids) == 500

    strict_longest_answers = 0
    correct_lengths = []
    incorrect_lengths = []
    for question in questions.for_course(course.id):
        correct_length = len(question.option_text(question.correct_answers[0]))
        wrong_lengths = [
            len(option.text)
            for option in question.options
            if option.id not in question.correct_answers
        ]
        strict_longest_answers += correct_length > max(wrong_lengths)
        correct_lengths.append(correct_length)
        incorrect_lengths.extend(wrong_lengths)
    assert strict_longest_answers / len(question_ids) <= 0.4
    assert abs(
        sum(correct_lengths) / len(correct_lengths)
        - sum(incorrect_lengths) / len(incorrect_lengths)
    ) <= 5
