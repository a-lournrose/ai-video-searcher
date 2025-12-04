ALTER TABLE frames
    ADD COLUMN source_id text NOT NULL DEFAULT '',
    ADD COLUMN at text NOT NULL DEFAULT '';