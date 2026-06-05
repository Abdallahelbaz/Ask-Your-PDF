from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):

    APP_NAME: str
    APP_VERSION: str
    LLM_API_KEY: str
    FILE_ALLOWED_TYPES: list
    FILE_MAX_SIZE_MB: int
    FILE_DEFAULT_CHUNK_SIZE: int


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
    VECTOR_DB_BACKEND_LITERAL:List[str]= None
    VECTOR_DB_PGVECTOR_INDEX_THRESHOLD: int

    DEFAULT_LANGUAGE:str ='en'
    
    POSTGRES_USERNAME:str
    POSTGRES_PASSWORD:str
    POSTGRES_HOST:str
    POSTGRES_PORT:int
    POSTGRES_MAIN_DB:str
    
    EXPAND_URL:str
    EXPAND_MODEL_ID:str

    class config:
        env_file = ".env"


def get_settings():
    return Settings()