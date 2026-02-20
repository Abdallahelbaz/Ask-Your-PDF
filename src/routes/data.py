from fastapi import FastAPI, APIRouter, Depends, UploadFile, status,Request
from fastapi.responses import JSONResponse
import os
from helpers.config import get_settings, Settings
from controllers import DataController, ProjectController, ProcessController
import aiofiles
from models import ResponseEnum
import logging
from .schemas.data import ProcessRequest
from models.ProjectModel import ProjectModel
from models.ChunkModel import ChunkModel
from models.schemas.Chunk import Chunk


data_rounter= APIRouter(
    prefix="/api/v1/data", 
    tags=["api_v1","data"]
    )

log=logging.getLogger('uvicorn.error')

@data_rounter.post("/upload/{project_id}")
async def upload_file(project_id: str, request: Request,
                       file: UploadFile,settings:Settings = Depends(get_settings)):
    
    project_model= await ProjectModel.create_instance(
        request.app.mongo_client
    )

    project= await project_model.get_or_create_project(project_id=project_id)
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
    file_path, file_id =datacontroller.generate_unique_filepath(
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
                "Signal": ResponseEnum.FILE_UPLOADED_SUCCESSFULLY.value,
                "file_id": file_id,

            }
        )

@data_rounter.post("/process/{project_id}")
async def data_processing(project_id: str, process_request: ProcessRequest, request: Request):
    file_id= process_request.file_id
    chunk_size= process_request.chunk_size
    overlap_size= process_request.overlap_size
    do_reset=process_request.do_reset

    project_model= await ProjectModel.create_instance(
        request.app.mongo_client
    )
    chunk_model= await ChunkModel.create_instance(
        request.app.mongo_client
    )


    project= await project_model.get_or_create_project(project_id=project_id)

    process_controller= ProcessController(project_id=project_id)
    file_content=process_controller.get_file_content(file_id)
    file_chunks= process_controller.process_file_content(
        file_content=file_content,
        file_id= file_id,
        chunk_size= chunk_size,
        overlap_size= overlap_size
    )

    if file_chunks is None or len(file_chunks) ==0:
            return JSONResponse (
            status=status.HTTP_400_BAD_REQUEST,
            content={
                "Signal": ResponseEnum.PROCESSING_FAILED.value
            }
        )

    file_chunks_records =[
        Chunk(
        chunk_text = chunk.page_content,
        chunk_metadata= chunk.metadata,
        chunk_order=i+1,
        chunk_project_id= project.id
         )
         for i, chunk in enumerate(file_chunks)
    ]


    if do_reset==1:
         _ =await chunk_model.delete_chunks_by_project_id(project_id=project.id)
    inserted_chunks=await chunk_model.insert_many(file_chunks_records)


    return JSONResponse (
            content={
                "Signal": ResponseEnum.PROCESSING_SUCCESS.value,
                "Inserted Chunks": inserted_chunks,
            }
        )