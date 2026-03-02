from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):

    APP_NAME: str
    APP_VERSION: str
    LLM_API_KEY: str
    FILE_ALLOWED_TYPES: list
    FILE_MAX_SIZE_MB: int
    FILE_DEFAULT_CHUNK_SIZE: int
    # Mongodb
    MONGODB_URL:str
    MONGODB_DATABASE:str

    GENERATION_BACKEND:str
    EMBEDDING_BACKEND:str

    QWEN_API_KEY: str
    QWEN_URL:str

    BGE_API_KEY:str = None
    BGE_URL:str= None

    GENERATION_MODEL_ID:str = None
    EMBEDDING_MODEL_ID: str= None
    EMBEDDING_MODEL_SIZE:int= None

    INPUT_DEFAULT_MAX_CHARS:int= None
    GENERATION_DEFAULT_MAX_TOKENS:int= None
    GENERATION_DEFAULT_TEMPERATURE: float= None

    VECTOR_DB_BACKEND:str
    VECTOR_DB_PATH:str
    VECTOR_DB_DISTANCE_METHPD:str

    DEFAULT_LANGUAGE:str ='en'

    class config:
        env_file = ".env"


def get_settings():
    return Settings()