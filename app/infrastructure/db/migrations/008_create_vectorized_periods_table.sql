CREATE TABLE vectorized_periods (
    id UUID PRIMARY KEY,
    source_id TEXT NOT NULL,
    start_at TEXT NOT NULL,
    end_at TEXT NOT NULL
);

CREATE UNIQUE INDEX ux_vectorized_periods_source_range
    ON vectorized_periods (source_id, start_at, end_at);

CREATE INDEX idx_vectorized_periods_source_id
    ON vectorized_periods (source_id);
