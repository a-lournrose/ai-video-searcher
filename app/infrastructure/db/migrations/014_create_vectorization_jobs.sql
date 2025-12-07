CREATE TABLE IF NOT EXISTS vectorization_jobs (
    id UUID PRIMARY KEY,
    source_id TEXT NOT NULL,
    ranges JSONB NOT NULL,
    status TEXT NOT NULL,
    progress DOUBLE PRECISION NOT NULL,
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_vectorization_jobs_source_id
    ON vectorization_jobs (source_id);

CREATE INDEX IF NOT EXISTS idx_vectorization_jobs_status
    ON vectorization_jobs (status);
