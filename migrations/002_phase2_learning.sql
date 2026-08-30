CREATE TABLE IF NOT EXISTS skills (
    skill_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS lesson_skills (
    course_id TEXT NOT NULL,
    lesson_id TEXT NOT NULL,
    skill_id TEXT NOT NULL,
    PRIMARY KEY (course_id, lesson_id, skill_id),
    FOREIGN KEY (skill_id) REFERENCES skills(skill_id)
);

CREATE TABLE IF NOT EXISTS quiz_questions (
    course_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    lesson_id TEXT,
    skill_id TEXT NOT NULL,
    topic TEXT NOT NULL,
    difficulty INTEGER NOT NULL CHECK(difficulty BETWEEN 1 AND 5),
    question_type TEXT NOT NULL CHECK(question_type IN ('single_choice', 'multiple_choice', 'short_answer')),
    prompt TEXT NOT NULL,
    options_json TEXT NOT NULL,
    correct_answers_json TEXT NOT NULL,
    explanation TEXT NOT NULL,
    incorrect_explanations_json TEXT NOT NULL,
    source_ref TEXT,
    content_hash TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0, 1)),
    updated_at TEXT NOT NULL,
    PRIMARY KEY (course_id, question_id),
    FOREIGN KEY (skill_id) REFERENCES skills(skill_id)
);

CREATE INDEX IF NOT EXISTS idx_quiz_questions_skill
ON quiz_questions(skill_id, topic, active);

CREATE TABLE IF NOT EXISTS quiz_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    skill_id TEXT NOT NULL,
    topic TEXT NOT NULL,
    answer_json TEXT NOT NULL,
    is_correct INTEGER NOT NULL CHECK(is_correct IN (0, 1)),
    response_time_seconds REAL NOT NULL CHECK(response_time_seconds >= 0),
    confidence INTEGER NOT NULL CHECK(confidence BETWEEN 1 AND 5),
    attempted_at TEXT NOT NULL,
    FOREIGN KEY (course_id, question_id)
        REFERENCES quiz_questions(course_id, question_id)
);

CREATE INDEX IF NOT EXISTS idx_quiz_attempts_skill_time
ON quiz_attempts(skill_id, attempted_at);

CREATE TABLE IF NOT EXISTS review_schedule (
    course_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    due_on TEXT NOT NULL,
    interval_days INTEGER NOT NULL CHECK(interval_days >= 1),
    streak INTEGER NOT NULL DEFAULT 0 CHECK(streak >= 0),
    last_correct INTEGER NOT NULL CHECK(last_correct IN (0, 1)),
    last_confidence INTEGER NOT NULL CHECK(last_confidence BETWEEN 1 AND 5),
    updated_at TEXT NOT NULL,
    PRIMARY KEY (course_id, question_id),
    FOREIGN KEY (course_id, question_id)
        REFERENCES quiz_questions(course_id, question_id)
);

CREATE INDEX IF NOT EXISTS idx_review_schedule_due
ON review_schedule(due_on);

CREATE TABLE IF NOT EXISTS practice_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id TEXT NOT NULL,
    mode TEXT NOT NULL CHECK(mode IN ('quiz', 'review', 'practice', 'mock_exam')),
    started_at TEXT NOT NULL,
    ended_at TEXT,
    duration_seconds REAL,
    target_question_count INTEGER NOT NULL CHECK(target_question_count > 0),
    correct_count INTEGER NOT NULL DEFAULT 0 CHECK(correct_count >= 0),
    answered_count INTEGER NOT NULL DEFAULT 0 CHECK(answered_count >= 0),
    status TEXT NOT NULL CHECK(status IN ('active', 'completed', 'abandoned'))
);

CREATE TABLE IF NOT EXISTS practice_session_questions (
    session_id INTEGER NOT NULL,
    position INTEGER NOT NULL,
    course_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    attempt_id INTEGER,
    PRIMARY KEY (session_id, position),
    FOREIGN KEY (session_id) REFERENCES practice_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (course_id, question_id)
        REFERENCES quiz_questions(course_id, question_id),
    FOREIGN KEY (attempt_id) REFERENCES quiz_attempts(id)
);

CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id TEXT,
    lesson_id TEXT,
    title TEXT NOT NULL,
    body_markdown TEXT NOT NULL,
    source_url TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_notes_context
ON notes(course_id, lesson_id, updated_at);
