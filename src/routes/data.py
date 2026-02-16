from fastapi import FastAPI, APIRouter, Depends, UploadFile, status
from fastapi.responses import JSONResponse
import os
from helpers.config import get_settings, Settings
from controllers import DataController, ProjectController
import aiofiles
from models import ResponseEnum
import logging

data_rounter= APIRouter(
    prefix="/api/v1/data", 
    tags=["api_v1","data"]
    )

log=logging.getLogger('uvicorn.error')

@data_rounter.post("/upload/{project_id}")
async def upload_file(project_id: str,
                       file: UploadFile,settings:Settings = Depends(get_settings)):
    datacontroller= DataController()
    is_valid, signal=  datacontroller.validate_file(file=file)
    
    if not is_valid:
        return JSONResponse (
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "Signal": signal
            }
        )

    project_dir_path= ProjectController().get_project_path(project_id=project_id)
    file_path=datacontroller.generate_unique_filename(
            original_file_name= file.filename,
            project_id=project_id
        )

    try:
        # write binary
        async with aiofiles.open(file_path, "wb") as f:
            while chunk := await file.read(settings.FILE_DEFAULT_CHUNK_SIZE):
                await f.write(chunk)
    except Exception as e:
        log.error(f"Error While Uploading: {e}")
        return JSONResponse (
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "Signal": ResponseEnum.FILE_UPLOADED_FAILED.value
            }
        )

    return JSONResponse (
            content={
                "Signal": ResponseEnum.FILE_UPLOADED_SUCCESSFULLY.value
            }
        )