CREATE TABLE search_jobs (
    id UUID PRIMARY KEY,
    title TEXT NOT NULL,
    text_query TEXT NOT NULL,
    source_id TEXT NOT NULL,
    start_at TEXT NOT NULL,
    end_at TEXT NOT NULL,
    progress FLOAT NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    error TEXT
);

CREATE INDEX idx_search_jobs_status ON search_jobs(status);
CREATE INDEX idx_search_jobs_source ON search_jobs(source_id);
