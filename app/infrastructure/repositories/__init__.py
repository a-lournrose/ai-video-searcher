from .frame_postgres_repository import FramePostgresRepository
from .object_postgres_repository import ObjectPostgresRepository
from .transport_attrs_postgres_repository import TransportAttributesPostgresRepository
from .person_attrs_postgres_repository import PersonAttributesPostgresRepository
from .embedding_postgres_repository import EmbeddingPostgresRepository

__all__ = [
    "FramePostgresRepository",
    "ObjectPostgresRepository",
    "TransportAttributesPostgresRepository",
    "PersonAttributesPostgresRepository",
    "EmbeddingPostgresRepository",
]