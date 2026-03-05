from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # Add this import
from dotenv import load_dotenv

load_dotenv(".env")
from routes import base, data, nlp
from motor.motor_asyncio import AsyncIOMotorClient
from helpers.config import get_settings
from stores.llm.LLMFactory import LLMFactory
from stores.vectordb.VectorDBFactory import VectorDBFactory
from stores.llm.templates.templateLLM import TemplateLLM

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

    app.mongo_connection = AsyncIOMotorClient(settings.MONGODB_URL)
    app.mongo_client = app.mongo_connection[settings.MONGODB_DATABASE]
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
    app.mongo_connection.close()
    app.vectordb_client.disconnect()

app.include_router(base.base_router)
app.include_router(data.data_rounter)
app.include_router(nlp.nlp_router)