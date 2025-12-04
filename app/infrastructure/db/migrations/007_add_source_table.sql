CREATE TABLE sources (
    id UUID PRIMARY KEY,
    source_id TEXT NOT NULL UNIQUE
);

CREATE INDEX idx_sources_source_id ON sources (source_id);