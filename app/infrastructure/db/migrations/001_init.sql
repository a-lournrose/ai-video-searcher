-- 001_init.sql
-- Базовая схема: frames, objects, transport_attrs, person_attrs, embeddings.

-- 1. Расширение pgvector для хранения эмбеддингов.
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. ENUM-типы для объектных и сущностных типов.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'object_type') THEN
        CREATE TYPE object_type AS ENUM ('PERSON', 'TRANSPORT');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'entity_type') THEN
        CREATE TYPE entity_type AS ENUM ('FRAME', 'OBJECT');
    END IF;
END $$;

-- 3. Таблица кадров видео.
CREATE TABLE frames (
    id UUID PRIMARY KEY,
    -- Время кадра в секундах от начала видео (можно float).
    timestamp_sec DOUBLE PRECISION NOT NULL
);

-- 4. Таблица объектов на кадрах.
CREATE TABLE objects (
    id UUID PRIMARY KEY,
    frame_id UUID NOT NULL REFERENCES frames(id) ON DELETE CASCADE,
    type object_type NOT NULL
);

CREATE INDEX idx_objects_frame_id ON objects(frame_id);

-- 5. Атрибуты транспортных средств.
CREATE TABLE transport_attrs (
    id UUID PRIMARY KEY,
    object_id UUID NOT NULL REFERENCES objects(id) ON DELETE CASCADE,
    -- Строковое представление HSV (например, "h=...,s=...,v=..." или JSON).
    color_hsv TEXT NOT NULL,
    -- Номерной знак (ГРЗ), строка в нормализованном формате.
    license_plate TEXT
);

CREATE INDEX idx_transport_attrs_object_id ON transport_attrs(object_id);

-- 6. Атрибуты людей.
CREATE TABLE person_attrs (
    id UUID PRIMARY KEY,
    object_id UUID NOT NULL REFERENCES objects(id) ON DELETE CASCADE,
    -- Цвет верхней одежды, HSV-строка.
    upper_color_hsv TEXT,
    -- Цвет нижней одежды, HSV-строка.
    lower_color_hsv TEXT
);

CREATE INDEX idx_person_attrs_object_id ON person_attrs(object_id);

-- 7. Эмбеддинги.
-- Здесь делаем более жёсткую модель:
--   - entity_type = FRAME  -> используется frame_id
--   - entity_type = OBJECT -> используется object_id
--   - CHECK гарантирует, что не будет "и того, и другого" или "ничего".
CREATE TABLE embeddings (
    id UUID PRIMARY KEY,
    entity_type entity_type NOT NULL,

    frame_id UUID,
    object_id UUID,

    -- Размерность 512 выбрана как типичная для CLIP/ruCLIP; при необходимости
    -- можно поменять в следующей миграции.
    vector vector(512) NOT NULL,

    CONSTRAINT embeddings_target_fk_frame
        FOREIGN KEY (frame_id) REFERENCES frames(id) ON DELETE CASCADE,

    CONSTRAINT embeddings_target_fk_object
        FOREIGN KEY (object_id) REFERENCES objects(id) ON DELETE CASCADE,

    CONSTRAINT embeddings_target_check CHECK (
        (entity_type = 'FRAME'  AND frame_id IS NOT NULL AND object_id IS NULL) OR
        (entity_type = 'OBJECT' AND object_id IS NOT NULL AND frame_id IS NULL)
    )
);

CREATE INDEX idx_embeddings_frame_id
    ON embeddings(frame_id)
    WHERE frame_id IS NOT NULL;

CREATE INDEX idx_embeddings_object_id
    ON embeddings(object_id)
    WHERE object_id IS NOT NULL;