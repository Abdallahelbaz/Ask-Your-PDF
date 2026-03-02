from .BaseController import BaseController
from models.schemas import Project, Chunk
from typing import List
from stores.llm.LLMEnum import DocumentTypeEnum
import json
import logging
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from collections import defaultdict
from typing import List, Dict, Any
from qdrant_client import models

class NLPController(BaseController):
    

    def __init__(self,vectordb_client,generation_client,embedding_client, templateLLM):
        super().__init__()
        self.vectordb_client=vectordb_client
        self.generation_client=generation_client
        self.embedding_client=embedding_client
        self.templateLLM=templateLLM
        self.log=logging.getLogger('uvicorn.error')

    def create_collection_name(self, project_id:str):
        return f"collection_{project_id}".strip()
    
    async def reset_vectordb_collection(self, project:Project):
        collection_name= self.create_collection_name(project.project_id)
        return self.vectordb_client.delete_collection(collection_name=collection_name)



    async def get_vectordb_collection_info(self, project:Project):
        collection_name=  self.create_collection_name(project.project_id)
        collection_info= await self.vectordb_client.get_collection_info(collection_name=collection_name)
        # it turns this string to json
        return json.loads(
            # it turns the reslut into string
            json.dumps(collection_info,default= lambda x:x.__dict__)
        )
    
    async def index_into_vectordb(self, project:Project, chunks:List[Chunk], chunks_ids:List[int], do_reset:bool=False):
        # 1 get Collection name
        collection_name= self.create_collection_name(project.project_id)
        # 2 manage items
        texts= [chunk.chunk_text for chunk in chunks]
        metadata= [data.chunk_metadata for data in chunks]

        vectors=[
            self.embedding_client.ebmed_text(text=text,document_type= DocumentTypeEnum.DOCUMENT.value)
            for text in texts
        ]
        # 3 create collection if not exists
        await self.vectordb_client.create_collection(
            collection_name=collection_name,
            embedding_size=self.embedding_client.embedding_size,
            do_reset=do_reset
        )


        # 4 insert into vectordb
        inserted=await self.vectordb_client.insert_many(
            collection_name=collection_name,
            texts=texts,
            metadata=metadata,
            vectors=vectors,
            record_ids=chunks_ids
        )

        return True

    
    
    # async def search_vectordb_collection(self,project:Project, text:str, limit: int=10):
    #     # 1 get collectioin name
    #     collection_name= self.create_collection_name(project.project_id)
    #     # 2 get text embedding vector
    #     vector = self.embedding_client.ebmed_text(
    #         text=text,
    #         document_type=DocumentTypeEnum.QUERY.value
    #     )
    #     if not vector or len(vector)==0:
    #         return False

    #     # 3 do semantic search
    #     result=await self.vectordb_client.search_by_vector(collection_name=collection_name, vector=vector, limit=limit)

    #     #         # it turns this string to json
    #     # return json.loads(
    #     #     # it turns the reslut into string
    #     #     json.dumps(result,default= lambda x:x.__dict__)
    #     # )

    #     return result



    async def search_vectordb_collection(self, project: Project, text: str, limit: int = 10, 
                                        use_hybrid: bool = True, vector_weight: float = 0.7):
        """
        Search vector database collection using either vector-only or hybrid search
        
        Args:
            project: Project object containing project_id
            text: Search query text
            limit: Number of results to return
            use_hybrid: If True, use hybrid search (vector + BM25). If False, use vector-only search
            vector_weight: Weight for vector search in hybrid mode (0-1). 
                        BM25 weight will be (1 - vector_weight)
        """
        # 1. Get collection name
        collection_name = self.create_collection_name(project.project_id)
        
        # 2. Get text embedding vector
        vector = self.embedding_client.ebmed_text(
            text=text,
            document_type=DocumentTypeEnum.QUERY.value
        )
        
        if not vector or len(vector) == 0:
            return []
        
        # 3. Perform search based on mode
        if use_hybrid:
            # Hybrid search (vector + BM25)
            print("use_hybrid")
            result = await self.vectordb_client.hybrid_search(
                collection_name=collection_name,
                query=text,
                vector=vector,
                vector_limit=limit * 2,  # Fetch more for reranking
                bm25_limit=limit * 2,     # Fetch more for reranking
                final_limit=limit,
                vector_weight=vector_weight
            )
        else:
            # Vector-only search
            result = await self.vectordb_client.search_by_vector(
                collection_name=collection_name,
                vector=vector,
                limit=limit
            )
        
        # Optional: Convert to JSON serializable format if needed
        # return json.loads(json.dumps([r.__dict__ for r in result]))
        
        return result




    async def answer_rag_question(self,project:Project, text:str, limit: int=10):
        answer, full_prompt,chat_history=None,None,None
        retrieved_doc=await self.search_vectordb_collection(
            project=project,
            text=text,
            limit=limit
        )

        # system_prompt=[
        #     "",
        #     ""
        # ]
        system_prompt=self.templateLLM.get(
            "rag", "system_prompt"
        )

        # docs_prompt=[]
        # for ids, doc in enumerate(retrieved_doc):
        #     docs_prompt.append(
        #           self.templateLLM.get(
        #             "rag","document_prompt",{
        #             "doc_num":ids+1,
        #             "chunk_text": doc.text
        #             }
        #         )
        #     )

        docs_prompt='\n'.join([
            self.templateLLM.get(
                    "rag","document_prompt",{
                    "doc_num":ids+1,
                    "chunk_text": doc.text
                    }
                )
            for ids, doc in enumerate(retrieved_doc)
        ])

        footer_prompt=self.templateLLM.get("rag","footer_prompt",{"query":text})

        chat_history=[
            self.generation_client.construct_prompt(
                prompt=system_prompt,
                role=self.generation_client.enums.SYSTEM.value
            )
        ]
        full_prompt= "\n\n".join([docs_prompt,footer_prompt ])

        answer=self.generation_client.generate_text(
             prompt=full_prompt,
             chat_history=chat_history
        )

        return footer_prompt , answer, full_prompt,chat_history