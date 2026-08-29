CREATE TABLE IF NOT EXISTS course_registrations (
    course_id TEXT PRIMARY KEY,
    schema_version INTEGER NOT NULL,
    manifest_hash TEXT NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL,
    last_seen_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS lesson_progress (
    course_id TEXT NOT NULL,
    lesson_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('started', 'completed')),
    started_at TEXT,
    completed_at TEXT,
    last_opened_at TEXT NOT NULL,
    PRIMARY KEY (course_id, lesson_id)
);

CREATE TABLE IF NOT EXISTS study_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id TEXT NOT NULL,
    lesson_id TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    duration_minutes REAL,
    status TEXT NOT NULL CHECK(status IN ('active', 'completed', 'abandoned'))
);

CREATE INDEX IF NOT EXISTS idx_study_sessions_lesson
ON study_sessions(course_id, lesson_id, started_at);

CREATE TABLE IF NOT EXISTS source_repositories (
    source_id TEXT NOT NULL,
    course_id TEXT NOT NULL,
    repo_url TEXT NOT NULL,
    local_path TEXT NOT NULL,
    commit_sha TEXT,
    last_sync_at TEXT,
    status TEXT NOT NULL,
    error_message TEXT,
    PRIMARY KEY (source_id, course_id)
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
