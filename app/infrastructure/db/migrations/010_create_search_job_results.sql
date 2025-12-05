CREATE TABLE search_job_results (
    id          UUID PRIMARY KEY,
    job_id      UUID NOT NULL REFERENCES search_jobs(id) ON DELETE CASCADE,
    frame_id    UUID NOT NULL REFERENCES frames(id),
    object_id   UUID REFERENCES objects(id),

    rank        INTEGER NOT NULL,              -- порядковый номер в выдаче
    final_score DOUBLE PRECISION NOT NULL,
    clip_score  DOUBLE PRECISION NOT NULL,
    color_score DOUBLE PRECISION NOT NULL,
    plate_score DOUBLE PRECISION NOT NULL
);

CREATE INDEX idx_search_job_results_job_id ON search_job_results(job_id);
CREATE INDEX idx_search_job_results_job_rank ON search_job_results(job_id, rank);