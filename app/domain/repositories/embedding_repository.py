from __future__ import annotations

from typing import Optional, Protocol

from app.domain.embedding import Embedding
from app.domain.value_objects import EmbeddingId


class EmbeddingRepository(Protocol):

    async def create(self, embedding: Embedding) -> None:
        ...

    async def find_by_id(self, embedding_id: EmbeddingId) -> Optional[Embedding]:
        ...
