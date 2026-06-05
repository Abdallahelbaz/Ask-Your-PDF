from fastapi import FastAPI, APIRouter, Depends, UploadFile, status,Request
from fastapi.responses import JSONResponse
import os
import logging
from .schemas.nlp import PushRequest, SearchRequest
from controllers import NLPController
from models.enums.ResponseEnums import ResponseEnum
from models.ProjectModel import ProjectModel
from models.ChunkModel import ChunkModel
from fastapi.middleware.cors import CORSMiddleware
from tqdm.auto import tqdm
from models.schemas import RetrievedDocument

nlp_router= APIRouter(
    prefix="/api/v1/nlp", 
    tags=["api_v1","data"]
    )
    



app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


log=logging.getLogger('uvicorn.error')

@nlp_router.post("/index/push/{project_id}")
async def index_project(request: Request, project_id: int, push_request: PushRequest):
    project_model= await ProjectModel.create_instance(
        client=request.app.db_client
    )
    project= await project_model.get_or_create_project(
        project_id=project_id
    )
    chunk_model= await ChunkModel.create_instance(
        client=request.app.db_client
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
        templateLLM=request.app.templateLLM,
        reranker=None,
        expander=None
    )
    has_records= True
    page_no=1
    inserted_items=0
    ids=0

    collection_name=nlp_controller.create_collection_name(project_id=project.project_id)

    await request.app.vectordb_client.create_collection(
        collection_name=collection_name,
        embedding_size=request.app.embedding_client.embedding_size,
        do_reset=push_request.do_reset
    )


    total_chunks_count=await chunk_model.get_total_chunks_count(project_id=project.project_id)
    progress=tqdm(total=total_chunks_count, position=0, desc="Vector Indexing")
    


    while has_records:
        log.error(f"page_no: {page_no}")
        page_chunks =await chunk_model.get_project_chunks(project_id=project.project_id,page_no=page_no)
        if len(page_chunks):
            page_no+=1
        
        if len(page_chunks)==0 or not page_chunks:
            has_records=False
            break

        chunk_ids=[c.chunk_id for c in page_chunks]
        ids+= len(page_chunks)

        is_inserted=await nlp_controller.index_into_vectordb(
            project=project,
            chunks=page_chunks,
            chunks_ids=chunk_ids,
        )
        if not is_inserted:
            return JSONResponse(
            content={
                "signal": ResponseEnum.INSERT_INTO_VECTORDB_ERROR.value
                }
            )
        progress.update(len(page_chunks))
        inserted_items+= len(page_chunks)
    
    return JSONResponse(
            content={
                "signal": ResponseEnum.INSERT_INTO_VECTORDB_SUCCESS.value,
                "Chunks_Inserted":inserted_items
                }
            )

@nlp_router.get("/index/info/{project_id}")
async def get_project_index_info(request: Request, project_id: int):

    log.error("iam in: get_project_index_info")
    project_model= await ProjectModel.create_instance(
        client=request.app.db_client
    )
    project= await project_model.get_or_create_project(
        project_id=project_id
    )
    nlp_controller=NLPController(
        vectordb_client=request.app.vectordb_client,
        embedding_client= request.app.embedding_client,
        generation_client=request.app.generation_client,
        templateLLM=request.app.templateLLM,
        reranker=None,
        expander=None
    )

    collection_info=await nlp_controller.get_vectordb_collection_info(project)
    return JSONResponse(
            content={
                "signal": ResponseEnum.VECTORDB_COLLECTION_INFO.value,
                "Collection_info":collection_info
                }
            )




@nlp_router.post("/index/search/{project_id}")
async def search_index(request:Request, project_id:int, search_request: SearchRequest):

    project_model= await ProjectModel.create_instance(
        client=request.app.db_client
    )
    project= await project_model.get_or_create_project(
        project_id=project_id
    )
    
    reranker =request.app.reranker
    nlp_controller=NLPController(
        vectordb_client=request.app.vectordb_client,
        embedding_client= request.app.embedding_client,
        generation_client=request.app.generation_client,
        templateLLM=request.app.templateLLM,
        reranker=reranker,
        expander=request.app.generation_client
    )
    results=await nlp_controller.search_vectordb_collection(
        project=project,
        text=search_request.text,
        limit=search_request.limit,
        client=request.app.db_client
    )

    print(type(results))

    return JSONResponse(
            content={
                "signal": ResponseEnum.VECTORDB_SEARCH_INFO.value,
                "results": [ result.dict() for result in results]
                }
            )



@nlp_router.post("/index/answer/{project_id}")
async def answer_rag(request:Request, project_id:int, search_request: SearchRequest):
    project_model= await ProjectModel.create_instance(
        client=request.app.db_client
    )
    project= await project_model.get_or_create_project(
        project_id=project_id
    )
    reranker =request.app.reranker
    nlp_controller=NLPController(
        vectordb_client=request.app.vectordb_client,
        embedding_client= request.app.embedding_client,
        generation_client=request.app.generation_client,
        templateLLM=request.app.templateLLM,
        reranker=reranker,
        expander=request.app.generation_client
    )
    query, answer, full_prompt, chat_history=await nlp_controller.answer_rag_question(
        project=project,
        text=search_request.text,
        limit=search_request.limit,
        client=request.app.db_client
    )

    return JSONResponse(
            content={
                "answer": answer,
                "full_prompt":full_prompt,
                "chat_history": chat_history, 
                "query": query
                }
            )

@nlp_router.post("/index/expand/{project_id}")
async def expand_query(request:Request, project_id:int, search_request: SearchRequest):
    
    reranker =request.app.reranker
    nlp_controller=NLPController(
        vectordb_client=request.app.vectordb_client,
        embedding_client= request.app.embedding_client,
        generation_client=request.app.generation_client,
        templateLLM=request.app.templateLLM,
        reranker=reranker, 
        expander=request.app.generation_client

    )
    answer=await nlp_controller.expand_rag_query(
        text=search_request.text
    )

    return JSONResponse(
            content={
                "answer": answer
                }
            )