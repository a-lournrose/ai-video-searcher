CREATE TABLE tasks (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    source_id TEXT NOT NULL,
    start_at TEXT NOT NULL,
    end_at TEXT NOT NULL
);

CREATE INDEX idx_tasks_source_id ON tasks (source_id);
CREATE INDEX idx_tasks_period ON tasks (start_at, end_at);