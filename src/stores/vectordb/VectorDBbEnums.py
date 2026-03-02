from enum import Enum

class VectorDBbEnums(Enum):
    QDRANT="QDRANT"


class DistanceMethodEnum(Enum):
    DOT= "dot"
    COSINE="cosine"