CREATE TABLE IF NOT EXISTS daily_study_plans (
    local_date TEXT PRIMARY KEY,
    available_minutes INTEGER NOT NULL CHECK(available_minutes >= 0),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS daily_study_plan_items (
    local_date TEXT NOT NULL,
    position INTEGER NOT NULL CHECK(position >= 0),
    course_id TEXT NOT NULL,
    lesson_id TEXT NOT NULL,
    PRIMARY KEY (local_date, position),
    FOREIGN KEY (local_date)
        REFERENCES daily_study_plans(local_date) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_daily_study_plan_items_lesson
ON daily_study_plan_items(course_id, lesson_id, local_date);
