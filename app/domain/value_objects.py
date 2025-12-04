from __future__ import annotations

from enum import Enum
from typing import NewType
from uuid import UUID

FrameId = NewType("FrameId", UUID)
ObjectId = NewType("ObjectId", UUID)
TransportAttrsId = NewType("TransportAttrsId", UUID)
PersonAttrsId = NewType("PersonAttrsId", UUID)
EmbeddingId = NewType("EmbeddingId", UUID)
TaskId = NewType("TaskId", UUID)
SourceRowId = NewType("SourceRowId", UUID)
VectorizedPeriodId = NewType("VectorizedPeriodId", UUID)
SearchJobId = NewType("SearchJobId", UUID)


class ObjectType(str, Enum):
    PERSON = "PERSON"
    TRANSPORT = "TRANSPORT"


class EmbeddingEntityType(str, Enum):
    FRAME = "FRAME"
    OBJECT = "OBJECT"
