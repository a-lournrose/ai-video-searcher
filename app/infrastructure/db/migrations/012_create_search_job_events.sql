CREATE TABLE search_job_events (
    id UUID PRIMARY KEY,
    job_id UUID NOT NULL REFERENCES search_jobs (id) ON DELETE CASCADE,
    track_id INTEGER NULL,
    object_id UUID NULL REFERENCES objects (id) ON DELETE SET NULL,
    score DOUBLE PRECISION NOT NULL
);

CREATE INDEX idx_search_job_events_job_id
    ON search_job_events (job_id);

CREATE INDEX idx_search_job_events_job_id_track_id
    ON search_job_events (job_id, track_id);

CREATE INDEX idx_search_job_events_job_id_score_desc
    ON search_job_events (job_id, score DESC);