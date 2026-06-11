-- v4_softskills.sql — Softskill Progress Tree
-- Stores per-user progress and custom success test for each softskill defined in softskills_tree.json

CREATE TABLE IF NOT EXISTS user_softskill_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    softskill_id VARCHAR(100) NOT NULL,
    success_criteria_test TEXT,
    current_level INTEGER DEFAULT 0,
    completed BOOLEAN DEFAULT 0,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, softskill_id)
);
