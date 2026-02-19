from fastapi import FastAPI
from dotenv import load_dotenv
load_dotenv(".env")
from routes import base, data
from motor.motor_asyncio import AsyncIOMotorClient
from helpers.config import get_settings

app = FastAPI()

@app.on_event('startup')
async def startup_client():
    settings = get_settings()

    app.mongo_connection= AsyncIOMotorClient(settings.MONGODB_URL)
    app.mongo_client= app.mongo_connection[settings.MONGODB_DATABASE]

@app.on_event('shutdown')
async def shutdown_client():
    app.mongo_connection.close()

app.include_router(base.base_router)
app.include_router(data.data_rounter)
