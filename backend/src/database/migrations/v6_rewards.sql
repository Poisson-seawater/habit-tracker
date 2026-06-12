-- v6_rewards.sql — Reward Shop
-- Stores per-user rewards that are purchasable using gold

CREATE TABLE IF NOT EXISTS rewards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    gold_cost INTEGER NOT NULL DEFAULT 0,
    required_softskill_id VARCHAR(100),
    required_goal_id INTEGER,
    is_one_time BOOLEAN DEFAULT 0,
    purchased_count INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(required_goal_id) REFERENCES goals(id) ON DELETE SET NULL
);
