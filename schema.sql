-- FamilyTaskManager PostgreSQL schema

CREATE TABLE IF NOT EXISTS families (
    chat_id BIGINT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS family_members (
    id SERIAL PRIMARY KEY,
    chat_id BIGINT REFERENCES families(chat_id) ON DELETE CASCADE,
    user_id BIGINT,
    username TEXT,
    first_name TEXT,
    joined_date TIMESTAMP,
    UNIQUE(chat_id, user_id)
);

CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    points INTEGER NOT NULL,
    time_minutes INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS assigned_tasks (
    id SERIAL PRIMARY KEY,
    chat_id BIGINT REFERENCES families(chat_id) ON DELETE CASCADE,
    task_id TEXT REFERENCES tasks(id) ON DELETE CASCADE,
    assigned_to BIGINT,
    assigned_by BIGINT,
    assigned_date TIMESTAMP,
    status TEXT,
    due_date TIMESTAMP,
    UNIQUE(chat_id, task_id, assigned_to)
);

CREATE TABLE IF NOT EXISTS completed_tasks (
    id SERIAL PRIMARY KEY,
    chat_id BIGINT,
    task_id TEXT,
    assigned_to BIGINT,
    assigned_by BIGINT,
    assigned_date TIMESTAMP,
    completed_date TIMESTAMP,
    points_earned INTEGER
);

CREATE TABLE IF NOT EXISTS user_stats (
    user_id BIGINT PRIMARY KEY,
    total_points INTEGER DEFAULT 0,
    tasks_completed INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1,
    badges TEXT[],
    streak INTEGER DEFAULT 0,
    last_task_date TIMESTAMP
);
