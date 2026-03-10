from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # Add this import
from dotenv import load_dotenv
from routes import base, data, nlp
from helpers.config import get_settings
from stores.llm.LLMFactory import LLMFactory
from stores.vectordb.VectorDBFactory import VectorDBFactory
from stores.llm.templates.templateLLM import TemplateLLM
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker


load_dotenv(".env")
app = FastAPI()

# ============ ADD CORS MIDDLEWARE HERE ============
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development only! Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],  # Allows all headers
)

@app.on_event('startup')
async def startup_client():
    settings = get_settings()

    postgre_conn=f"postgresql+asyncpg://{settings.POSTGRES_USERNAME}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_MAIN_DB}"
    app.db_engine=create_async_engine(postgre_conn)


    app.db_client = sessionmaker(
        app.db_engine, class_= AsyncSession, expire_on_commit=False
    )
    factory = LLMFactory(settings)

    app.generation_client = factory.create(provider=settings.GENERATION_BACKEND)
    app.generation_client.set_generation_model(model_id=settings.GENERATION_MODEL_ID)

    app.embedding_client = factory.create(provider=settings.EMBEDDING_BACKEND)
    app.embedding_client.set_embedding_model(
        model_id=settings.EMBEDDING_MODEL_ID,
        model_size=settings.EMBEDDING_MODEL_SIZE
    )
    
    vectordb_factory = VectorDBFactory(settings)
    app.vectordb_client = vectordb_factory.create(provider=settings.VECTOR_DB_BACKEND)
    app.vectordb_client.connect()
    
    app.templateLLM = TemplateLLM(
        language=settings.DEFAULT_LANGUAGE
    )

@app.on_event('shutdown')
async def shutdown_client():
    app.vectordb_client.disconnect()
    app.db_engine.dispose()
app.include_router(base.base_router)
app.include_router(data.data_rounter)
app.include_router(nlp.nlp_router)