from enum import Enum

class VectorDBbEnums(Enum):
    QDRANT="QDRANT"
    PGVECTOR="PGVECTOR"


class DistanceMethodEnum(Enum):
    DOT= "dot"
    COSINE="cosine"


class PgVectorTableEnums(Enum):
    ID='id'
    TEXT="text"
    VECTOR="vector"
    CHUNK_ID="chunk_id"
    METADATA="metadata"
    _PREFIX="pgvector"


class PgVectorDistanceMethodEnum(Enum):
    DOT= "vector_l2_ops"
    COSINE="vector_cosine_ops"

class PgVectorIndexEnum(Enum):
    HNSW="knsw"
    IVFFLAT="ivfflat"