from enum import Enum

class LLMEnum(Enum):

    QWEN="QWEN"
    BGE="BGE"


class OpenAIEnums(Enum):
    SYSTEM="system"
    USER="user"
    ASSISTANT="assistant"

class BGEEnum(Enum):
    SYSTEM="SYS"
    USER="user"
    ASSISTANT="assistant"

class DocumentTypeEnum(Enum):
    DOCUMENT="document"
    QUERY="query"