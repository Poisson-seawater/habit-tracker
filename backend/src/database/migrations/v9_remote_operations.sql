-- v9_remote_operations.sql
-- Idempotency journal for remote API mutations.

CREATE TABLE IF NOT EXISTS remote_operations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    idempotency_key VARCHAR(100) NOT NULL,
    request_hash VARCHAR(64) NOT NULL,
    method VARCHAR(10) NOT NULL,
    path VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'in_progress',
    http_status INTEGER,
    response_body TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS ix_remote_operations_user_id
ON remote_operations(user_id);
