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
from models.AssetModel import AssetModel
from models.schemas import Chunk, Asset
from models.enums.AssetTypeEnum import AssetTypeEnum
from fastapi.middleware.cors import CORSMiddleware
from controllers import NLPController

data_rounter= APIRouter(
    prefix="/api/v1/data", 
    tags=["api_v1","data"]
    )


app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

log=logging.getLogger('uvicorn.error')

@data_rounter.post("/upload/{project_id}")
async def upload_file(project_id: int, request: Request,
                       file: UploadFile,settings:Settings = Depends(get_settings)):
    
    project_model= await ProjectModel.create_instance(
        request.app.db_client
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
    
    asset_model= await AssetModel.create_instance(
         request.app.db_client
    )

    resource= Asset(
         asset_project_id=project.project_id,
         asset_type=AssetTypeEnum.FILE.value,
         asset_name=file_id,
         asset_size= os.path.getsize(file_path),
    )

    asset_record= await asset_model.create_asset(resource)

    return JSONResponse (
            content={
                "Signal": ResponseEnum.FILE_UPLOADED_SUCCESSFULLY.value,
                "file_id": str(asset_record.asset_id),

            }
        )

@data_rounter.post("/process_parent/{project_id}")
async def data_processing_parent(project_id: int, process_request: ProcessRequest, request: Request):

    # 1. Initialization
    chunk_size = process_request.chunk_size
    overlap_size = process_request.overlap_size
    do_reset = process_request.do_reset

    project_model = await ProjectModel.create_instance(request.app.db_client)
    chunk_model = await ChunkModel.create_instance(request.app.db_client)
    asset_model = await AssetModel.create_instance(request.app.db_client)
    
    project = await project_model.get_or_create_project(project_id=project_id)
    
    # 2. Get files to process
    project_files_ids = {}
    if process_request.file_id:
        asset_record = await asset_model.get_asset_record(
            asset_project_id=project.project_id,
            asset_name=process_request.file_id
        )
        project_files_ids = {asset_record.asset_id: asset_record.asset_name}
    else:
        project_files = await asset_model.get_all_project_assets(
            asset_project_id=project.project_id,
            asset_type=AssetTypeEnum.FILE.value
        )
        project_files_ids = {record.asset_id: record.asset_name for record in project_files}
    
    if len(project_files_ids) == 0:
        return JSONResponse(content={"Signal": ResponseEnum.NO_FILES_SIGNAL.value})
    
    process_controller = ProcessController(project_id=project_id)
    
    # 3. Reset logic
    if do_reset == 1:
        await chunk_model.delete_chunks_by_project_id(project_id=project.project_id)
        # Note: If you have a vector collection to clear, add it here later

    inserted_parents = 0
    inserted_children = 0
    no_files = 0
    
    # 4. Processing Loop
    for asset_id, file_id in project_files_ids.items():
        file_content = process_controller.get_file_content(file_id)

        if file_content is None:
            log.error(f"This File: {file_id} doesn't Exist!")
            continue

        # This should return (List[Parent_Objects], List[Child_Data_Dicts])
        parent_objs, child_data_list = process_controller.process_file_content(
            file_content=file_content,
            asset_id=asset_id,
            project_id=project.project_id,
            chunk_size=chunk_size,
            overlap_size=overlap_size
        )

        if not parent_objs:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"Signal": ResponseEnum.PROCESSING_FAILED.value}
            )

        # 5. Insert logic (Handles the SQL relationship between parent and child)
        all_inserted_children = await chunk_model.insert_parent_child_chunks(
            parent_chunks=parent_objs,
            child_data_list=child_data_list
        )
        
        inserted_parents += len(parent_objs)
        inserted_children += len(all_inserted_children)
        no_files += 1

    return JSONResponse(
        content={
            "Signal": ResponseEnum.PROCESSING_SUCCESS.value,
            "Inserted_Parents": inserted_parents,
            "Inserted_Children": inserted_children,
            "Total_Chunks": inserted_parents + inserted_children,
            "No_files": no_files
        }
    )




@data_rounter.post("/process/{project_id}")
async def data_processing(project_id: int, process_request: ProcessRequest, request: Request):

    chunk_size= process_request.chunk_size
    overlap_size= process_request.overlap_size
    do_reset=process_request.do_reset

    project_model= await ProjectModel.create_instance(
        request.app.db_client
    )
    chunk_model= await ChunkModel.create_instance(
        request.app.db_client
    )
    project= await project_model.get_or_create_project(project_id=project_id)
    project_files_ids={}
    asset_model= await AssetModel.create_instance(
        request.app.db_client
        )
    nlp_controller=NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        templateLLM=request.app.templateLLM,
        reranker=None,
        expander=None
         
    )
    if process_request.file_id:
        asset_record= await asset_model.get_asset_record(
             asset_project_id= project.project_id,
             asset_name=process_request.file_id
        )
        project_files_ids={
             asset_record.asset_id: asset_record.asset_name
        }


    else:

        project_files= await asset_model.get_all_project_assets(
            asset_project_id= project.project_id,
            asset_type= AssetTypeEnum.FILE.value
        )
        project_files_ids={
            record.asset_id: record.asset_name
            for record in project_files
        }
    
    if len(project_files_ids)==0:
        return JSONResponse (
            content={
                "Signal": ResponseEnum.NO_FILES_SIGNAL.value,

            }
        )
    process_controller= ProcessController(project_id=project_id)
    inserted_chunks=0
    no_files=0
    if do_reset==1:
            collection_name=nlp_controller.create_collection_name(project.project_id)
            _ =await chunk_model.delete_chunks_by_project_id(project_id=project.project_id)
            await request.app.vectordb_client.delete_collection(collection_name)

    for asset_id, file_id in project_files_ids.items():
        
        file_content=process_controller.get_file_content(file_id)

        if file_content is None:
            log.error(f"This File: {file_content} doesn't Exist!")
            continue

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
            chunk_project_id= project.project_id,
            chunk_asset_id=asset_id
            )
            for i, chunk in enumerate(file_chunks)
        ]
        inserted_chunks+=await chunk_model.insert_many(file_chunks_records)
        no_files+=1

    

    return JSONResponse (
            content={
                "Signal": ResponseEnum.PROCESSING_SUCCESS.value,
                "Inserted Chunks": inserted_chunks,
                "No_files":no_files
            }
        )