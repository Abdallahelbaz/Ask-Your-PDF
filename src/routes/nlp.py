from fastapi import FastAPI, APIRouter, Depends, UploadFile, status,Request
from fastapi.responses import JSONResponse
import os
import logging
from .schemas.nlp import PushRequest, SearchRequest
from controllers import NLPController
from models.enums.ResponseEnums import ResponseEnum
from models.ProjectModel import ProjectModel
from models.ChunkModel import ChunkModel

nlp_router= APIRouter(
    prefix="/api/v1/nlp", 
    tags=["api_v1","data"]
    )
    

log=logging.getLogger('uvicorn.error')

@nlp_router.post("/index/push/{project_id}")
async def index_project(request: Request, project_id: str, push_request: PushRequest):
    project_model= await ProjectModel.create_instance(
        client=request.app.mongo_client
    )
    project= await project_model.get_or_create_project(
        project_id=project_id
    )
    chunk_model= await ChunkModel.create_instance(
        client=request.app.mongo_client
    )


    if not project:
        return JSONResponse(
            content={
                "signal": ResponseEnum.PROJECT_NOT_FOUND.value
            }
        )
    nlp_controller=NLPController(
        vectordb_client=request.app.vectordb_client,
        embedding_client= request.app.embedding_client,
        generation_client=request.app.generation_client,
        templateLLM=request.app.templateLLM
    )
    has_records= True
    page_no=1
    inserted_items=0
    ids=0

    while has_records:
        log.error(f"page_no: {page_no}")
        page_chunks =await chunk_model.get_project_chunks(project_id=project.id,page_no=page_no)
        if len(page_chunks):
            page_no+=1
        
        if len(page_chunks)==0 or not page_chunks:
            has_records=False
            break

        chunk_ids=list(range(ids,ids+len(page_chunks)))
        ids+= len(page_chunks)

        is_inserted=await nlp_controller.index_into_vectordb(
            project=project,
            chunks=page_chunks,
            do_reset=push_request.do_reset,
            chunks_ids=chunk_ids,
        )
        if not is_inserted:
            return JSONResponse(
            content={
                "signal": ResponseEnum.INSERT_INTO_VECTORDB_ERROR.value
                }
            )
        inserted_items+= len(page_chunks)
    
    return JSONResponse(
            content={
                "signal": ResponseEnum.INSERT_INTO_VECTORDB_SUCCESS.value,
                "Chunks_Inserted":inserted_items
                }
            )

@nlp_router.get("/index/info/{project_id}")
async def get_project_index_info(request: Request, project_id: str):

    log.error("iam in: get_project_index_info")
    project_model= await ProjectModel.create_instance(
        client=request.app.mongo_client
    )
    project= await project_model.get_or_create_project(
        project_id=project_id
    )
    nlp_controller=NLPController(
        vectordb_client=request.app.vectordb_client,
        embedding_client= request.app.embedding_client,
        generation_client=request.app.generation_client,
        templateLLM=request.app.templateLLM
    )

    collection_info=await nlp_controller.get_vectordb_collection_info(project)
    return JSONResponse(
            content={
                "signal": ResponseEnum.VECTORDB_COLLECTION_INFO.value,
                "Collection_info":collection_info
                }
            )

@nlp_router.post("/index/search/{project_id}")
async def search_index(request:Request, project_id:str, search_request: SearchRequest):
    project_model= await ProjectModel.create_instance(
        client=request.app.mongo_client
    )
    project= await project_model.get_or_create_project(
        project_id=project_id
    )
    nlp_controller=NLPController(
        vectordb_client=request.app.vectordb_client,
        embedding_client= request.app.embedding_client,
        generation_client=request.app.generation_client,
        templateLLM=request.app.templateLLM
    )
    results=await nlp_controller.search_vectordb_collection(
        project=project,
        text=search_request.text,
        limit=search_request.limit,
    )

    return JSONResponse(
            content={
                "signal": ResponseEnum.VECTORDB_SEARCH_INFO.value,
                "results": [ result.dict() for result in results]
                }
            )



@nlp_router.post("/index/answer/{project_id}")
async def answer_rag(request:Request, project_id:str, search_request: SearchRequest):
    project_model= await ProjectModel.create_instance(
        client=request.app.mongo_client
    )
    project= await project_model.get_or_create_project(
        project_id=project_id
    )
    nlp_controller=NLPController(
        vectordb_client=request.app.vectordb_client,
        embedding_client= request.app.embedding_client,
        generation_client=request.app.generation_client,
        templateLLM=request.app.templateLLM

    )
    query, answer, full_prompt, chat_history=await nlp_controller.answer_rag_question(
        project=project,
        text=search_request.text,
        limit=search_request.limit
    )

    return JSONResponse(
            content={
                "answer": answer,
                "full_prompt":full_prompt,
                "chat_history": chat_history, 
                "query": query
                }
            )