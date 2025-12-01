from __future__ import annotations

import asyncio
from typing import List
from uuid import uuid4

from app.domain import (
    Frame,
    Object,
    TransportAttributes,
    PersonAttributes,
    Embedding,
)
from app.domain.value_objects import (
    FrameId,
    ObjectId,
    TransportAttrsId,
    PersonAttrsId,
    EmbeddingId,
    ObjectType,
    EmbeddingEntityType,
)
from app.infrastructure.db.postgres import PostgresDatabase, load_config_from_env
from app.infrastructure.repositories import (
    FramePostgresRepository,
    ObjectPostgresRepository,
    TransportAttributesPostgresRepository,
    PersonAttributesPostgresRepository,
    EmbeddingPostgresRepository,
)


EMBEDDING_DIM = 512


def _make_dummy_vector(dim: int = EMBEDDING_DIM, base: float = 0.001) -> List[float]:
    """
    Генерирует детерминированный «тупой» вектор для теста.
    Без рандома, чтобы результат был воспроизводим.
    """
    return [base * (i + 1) for i in range(dim)]


async def _test_frames(frame_repo: FramePostgresRepository) -> Frame:
    frame = Frame(
        id=FrameId(uuid4()),
        timestamp_sec=12.34,
    )

    await frame_repo.create(frame)
    loaded = await frame_repo.find_by_id(frame.id)

    assert loaded is not None, "Frame not found after create"
    assert loaded.id == frame.id, "Frame id mismatch"
    assert loaded.timestamp_sec == frame.timestamp_sec, "Frame timestamp mismatch"

    print(f"[OK] Frame test passed: {frame.id}")
    return frame


async def _test_objects(
    object_repo: ObjectPostgresRepository,
    frame: Frame,
) -> tuple[Object, Object]:
    transport = Object(
        id=ObjectId(uuid4()),
        frame_id=frame.id,
        type=ObjectType.TRANSPORT,
    )
    person = Object(
        id=ObjectId(uuid4()),
        frame_id=frame.id,
        type=ObjectType.PERSON,
    )

    await object_repo.create(transport)
    await object_repo.create(person)

    loaded_transport = await object_repo.find_by_id(transport.id)
    loaded_person = await object_repo.find_by_id(person.id)

    assert loaded_transport is not None, "Transport object not found after create"
    assert loaded_person is not None, "Person object not found after create"

    assert loaded_transport.type == ObjectType.TRANSPORT, "Transport type mismatch"
    assert loaded_person.type == ObjectType.PERSON, "Person type mismatch"

    assert loaded_transport.frame_id == frame.id, "Transport frame_id mismatch"
    assert loaded_person.frame_id == frame.id, "Person frame_id mismatch"

    print(f"[OK] Object test passed: transport={transport.id}, person={person.id}")
    return transport, person


async def _test_transport_attrs(
    repo: TransportAttributesPostgresRepository,
    transport: Object,
) -> TransportAttributes:
    attrs = TransportAttributes(
        id=TransportAttrsId(uuid4()),
        object_id=transport.id,
        color_hsv="h=30,s=0.8,v=0.9",
        license_plate="A123BC77",
    )

    await repo.create(attrs)
    loaded = await repo.find_by_id(attrs.id)

    assert loaded is not None, "TransportAttributes not found after create"
    assert loaded.id == attrs.id, "TransportAttributes id mismatch"
    assert loaded.object_id == attrs.object_id, "TransportAttributes object_id mismatch"
    assert loaded.color_hsv == attrs.color_hsv, "TransportAttributes color_hsv mismatch"
    assert loaded.license_plate == attrs.license_plate, "TransportAttributes plate mismatch"

    print(f"[OK] TransportAttributes test passed: {attrs.id}")
    return attrs


async def _test_person_attrs(
    repo: PersonAttributesPostgresRepository,
    person: Object,
) -> PersonAttributes:
    attrs = PersonAttributes(
        id=PersonAttrsId(uuid4()),
        object_id=person.id,
        upper_color_hsv="h=120,s=0.7,v=0.8",
        lower_color_hsv="h=210,s=0.6,v=0.9",
    )

    await repo.create(attrs)
    loaded = await repo.find_by_id(attrs.id)

    assert loaded is not None, "PersonAttributes not found after create"
    assert loaded.id == attrs.id, "PersonAttributes id mismatch"
    assert loaded.object_id == attrs.object_id, "PersonAttributes object_id mismatch"
    assert loaded.upper_color_hsv == attrs.upper_color_hsv, "PersonAttributes upper_color_hsv mismatch"
    assert loaded.lower_color_hsv == attrs.lower_color_hsv, "PersonAttributes lower_color_hsv mismatch"

    print(f"[OK] PersonAttributes test passed: {attrs.id}")
    return attrs


async def _test_embeddings(
    repo: EmbeddingPostgresRepository,
    frame: Frame,
    transport: Object,
    person: Object,
) -> None:
    frame_embedding = Embedding(
        id=EmbeddingId(uuid4()),
        entity_type=EmbeddingEntityType.FRAME,
        frame_id=frame.id,
        object_id=None,
        vector=_make_dummy_vector(base=0.001),
    )

    transport_embedding = Embedding(
        id=EmbeddingId(uuid4()),
        entity_type=EmbeddingEntityType.OBJECT,
        frame_id=None,
        object_id=transport.id,
        vector=_make_dummy_vector(base=0.002),
    )

    person_embedding = Embedding(
        id=EmbeddingId(uuid4()),
        entity_type=EmbeddingEntityType.OBJECT,
        frame_id=None,
        object_id=person.id,
        vector=_make_dummy_vector(base=0.003),
    )

    await repo.create(frame_embedding)
    await repo.create(transport_embedding)
    await repo.create(person_embedding)

    loaded_frame = await repo.find_by_id(frame_embedding.id)
    loaded_transport = await repo.find_by_id(transport_embedding.id)
    loaded_person = await repo.find_by_id(person_embedding.id)

    assert loaded_frame is not None, "Frame embedding not found after create"
    assert loaded_transport is not None, "Transport embedding not found after create"
    assert loaded_person is not None, "Person embedding not found after create"

    assert loaded_frame.entity_type == EmbeddingEntityType.FRAME, "Frame embedding entity_type mismatch"
    assert loaded_frame.frame_id == frame.id, "Frame embedding frame_id mismatch"
    assert loaded_frame.object_id is None, "Frame embedding object_id should be None"

    assert loaded_transport.entity_type == EmbeddingEntityType.OBJECT, "Transport embedding entity_type mismatch"
    assert loaded_transport.object_id == transport.id, "Transport embedding object_id mismatch"
    assert loaded_transport.frame_id is None, "Transport embedding frame_id should be None"

    assert loaded_person.entity_type == EmbeddingEntityType.OBJECT, "Person embedding entity_type mismatch"
    assert loaded_person.object_id == person.id, "Person embedding object_id mismatch"
    assert loaded_person.frame_id is None, "Person embedding frame_id should be None"

    assert len(loaded_frame.vector) == EMBEDDING_DIM, "Frame embedding vector dim mismatch"
    assert len(loaded_transport.vector) == EMBEDDING_DIM, "Transport embedding vector dim mismatch"
    assert len(loaded_person.vector) == EMBEDDING_DIM, "Person embedding vector dim mismatch"

    print(f"[OK] Embedding test passed: "
          f"frame={frame_embedding.id}, transport={transport_embedding.id}, person={person_embedding.id}")


async def run_full_smoke_test() -> None:
    config = load_config_from_env()
    db = PostgresDatabase(config)
    await db.connect()

    try:
        frame_repo = FramePostgresRepository(db)
        object_repo = ObjectPostgresRepository(db)
        transport_attrs_repo = TransportAttributesPostgresRepository(db)
        person_attrs_repo = PersonAttributesPostgresRepository(db)
        embedding_repo = EmbeddingPostgresRepository(db)

        print("=== Running full infrastructure smoke test ===")

        frame = await _test_frames(frame_repo)
        transport, person = await _test_objects(object_repo, frame)
        await _test_transport_attrs(transport_attrs_repo, transport)
        await _test_person_attrs(person_attrs_repo, person)
        await _test_embeddings(embedding_repo, frame, transport, person)

        print("=== ALL TESTS PASSED ===")

    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(run_full_smoke_test())
