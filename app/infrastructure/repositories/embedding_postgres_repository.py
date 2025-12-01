from __future__ import annotations

from typing import Optional, List, Any

from asyncpg import Record

from app.domain.embedding import Embedding
from app.domain.value_objects import (
    EmbeddingId,
    FrameId,
    ObjectId,
    EmbeddingEntityType,
)
from app.domain.repositories.embedding_repository import EmbeddingRepository
from app.infrastructure.db.postgres import PostgresDatabase


def _vector_to_literal(values: List[float]) -> str:
    """
    Преобразует список чисел в строку формата, понятного pgvector.

    Пример: [0.1, 0.2, 0.3] -> "[0.1,0.2,0.3]"
    """
    inner = ",".join(str(v) for v in values)
    return f"[{inner}]"


def _literal_to_vector(raw: Any) -> List[float]:
    """
    Преобразует значение из БД (обычно строка вида "[0.1,0.2,...]")
    в список float.

    Если драйвер вдруг вернёт уже список/итерируемое — аккуратно
    приведём к list[float].
    """
    if raw is None:
        return []

    # Если драйвер уже вернул последовательность — просто приведём к float.
    if isinstance(raw, (list, tuple)):
        return [float(x) for x in raw]

    # Ожидаем строку вида "[0.1,0.2,...]".
    s = str(raw).strip()

    # Уберём возможные квадратные скобки.
    if s.startswith("[") and s.endswith("]"):
        s = s[1:-1].strip()

    if not s:
        return []

    parts = s.split(",")
    return [float(p) for p in parts if p.strip()]


class EmbeddingPostgresRepository(EmbeddingRepository):
    """
    Реализация EmbeddingRepository поверх PostgreSQL (таблица embeddings).
    """

    def __init__(self, db: PostgresDatabase) -> None:
        self._db = db

    async def create(self, embedding: Embedding) -> None:
        sql = """
        INSERT INTO embeddings (id, entity_type, frame_id, object_id, vector)
        VALUES ($1, $2, $3, $4, $5);
        """

        vector_literal = _vector_to_literal(embedding.vector)

        await self._db.execute(
            sql,
            embedding.id,
            embedding.entity_type.value,  # 'FRAME' / 'OBJECT'
            embedding.frame_id,
            embedding.object_id,
            vector_literal,               # <-- передаём строку, которую парсит pgvector
        )

    async def find_by_id(self, embedding_id: EmbeddingId) -> Optional[Embedding]:
        sql = """
        SELECT id, entity_type, frame_id, object_id, vector
        FROM embeddings
        WHERE id = $1;
        """

        row = await self._db.fetchrow( sql, embedding_id)
        if row is None:
            return None

        return self._map_row_to_embedding(row)

    @staticmethod
    def _map_row_to_embedding(row: Record) -> Embedding:
        """
        Маппинг строки из БД в доменную модель Embedding.

        asyncpg для pgvector без кастомного кодека, как правило,
        возвращает значение как строку. Мы приводим это к list[float].
        """
        vector = _literal_to_vector(row["vector"])

        frame_id = row["frame_id"]
        object_id = row["object_id"]

        return Embedding(
            id=EmbeddingId(row["id"]),
            entity_type=EmbeddingEntityType(row["entity_type"]),
            frame_id=FrameId(frame_id) if frame_id is not None else None,
            object_id=ObjectId(object_id) if object_id is not None else None,
            vector=vector,
        )