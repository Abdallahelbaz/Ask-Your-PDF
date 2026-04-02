from .BaseController import BaseController
from models.schemas import Project, Chunk
from typing import List
from stores.llm.LLMEnum import DocumentTypeEnum
from models.schemas import RetrievedDocument
import json
import logging
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from collections import defaultdict
from typing import List, Dict, Any
from qdrant_client import models
# from flashrank import Ranker, RerankRequest
# from sentence_transformers import CrossEncoder


class NLPController(BaseController):
    

    def __init__(self,vectordb_client,generation_client,embedding_client, templateLLM, reranker, expander):
        super().__init__()
        self.vectordb_client=vectordb_client
        self.generation_client=generation_client
        self.embedding_client=embedding_client
        self.templateLLM=templateLLM
        self.log=logging.getLogger('uvicorn.error')
        # self.ranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2")
        # self.reranker= CrossEncoder("BAAI/bge-reranker-large")
        self.reranker=reranker
        self.expander=expander

    def create_collection_name(self, project_id:str):
        return f"collection_{project_id}".strip()
    
    async def reset_vectordb_collection(self, project:Project):
        collection_name= self.create_collection_name(project.project_id)
        return await self.vectordb_client.delete_collection(collection_name=collection_name)



    async def get_vectordb_collection_info(self, project:Project):
        collection_name=  self.create_collection_name(project.project_id)
        collection_info= await self.vectordb_client.get_collection_info(collection_name=collection_name)
        # it turns this string to json
        return json.loads(
            # it turns the reslut into string
            json.dumps(collection_info,default= lambda x:x.__dict__)
        )
    

    async def index_into_vectordb_parent(self, project:Project, chunks:List[Chunk], chunks_ids:List[int], do_reset:bool=False):
        # 1. Get Collection name
        collection_name = self.create_collection_name(project.project_id)
        
        # 2. Filter everything TOGETHER
        # We only want chunks that have a parent_id (the children)
        filtered_data = [
            (c.chunk_text, c.chunk_metadata, cid) 
            for c, cid in zip(chunks, chunks_ids) 
            if c.parent_id is not None
        ]

        # 3. Check if we actually have anything to embed
        if not filtered_data:
            print("No child chunks found in this batch, skipping...")
            return True

        # Unpack the filtered results
        texts, metadata, record_ids = zip(*filtered_data)
        texts = list(texts)
        metadata = list(metadata)
        record_ids = list(record_ids)

        # 4. Now embed (this won't crash because texts is not empty)
        vectors = self.embedding_client.embed_text(
            text=texts, 
            document_type=DocumentTypeEnum.DOCUMENT.value
        )

        # 5. Create collection
        await self.vectordb_client.create_collection(
            collection_name=collection_name,
            embedding_size=self.embedding_client.embedding_size,
            do_reset=do_reset
        )

        # 6. Insert (record_ids is now the same length as texts and vectors)
        inserted = await self.vectordb_client.insert_many(
            collection_name=collection_name,
            texts=texts,
            metadata=metadata,
            vectors=vectors,
            record_ids=record_ids
        )

        return True


    async def index_into_vectordb(self, project:Project, chunks:List[Chunk], chunks_ids:List[int], do_reset:bool=False):
        # 1 get Collection name
        collection_name= self.create_collection_name(project.project_id)
        # 2 manage items
        texts= [chunk.chunk_text for chunk in chunks ]
        metadata= [data.chunk_metadata for data in chunks]
    
        vectors= self.embedding_client.embed_text(text=texts,document_type= DocumentTypeEnum.DOCUMENT.value)

       
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




    # async def index_into_vectordb(
    #     self,
    #     project: Project,
    #     chunks: List[Chunk],
    #     chunks_ids: List[int],
    #     do_reset: bool = False):

    #     collection_name = self.create_collection_name(project.project_id)

    #     texts = []
    #     metadata = []
    #     valid_ids = []

    #     for chunk, cid in zip(chunks, chunks_ids):

    #         if chunk.chunk_text is None:
    #             continue

    #         text = chunk.chunk_text.strip()

    #         if len(text) < 5:
    #             continue

    #         texts.append(text)
    #         metadata.append(chunk.chunk_metadata)
    #         valid_ids.append(cid)

    #     # embeddings
    #     vectors = self.embedding_client.embed_text(
    #         text=texts,
    #         document_type=DocumentTypeEnum.DOCUMENT.value
    #     )

    #     await self.vectordb_client.create_collection(
    #         collection_name=collection_name,
    #         embedding_size=self.embedding_client.embedding_size,
    #         do_reset=do_reset
    #     )

    #     inserted = await self.vectordb_client.insert_many(
    #         collection_name=collection_name,
    #         texts=texts,
    #         metadata=metadata,
    #         vectors=vectors,
    #         record_ids=valid_ids
    #     )

    #     return True
    async def search_vectordb_collection_reranker(
        self, 
        project: Project, 
        text: str, 
        limit: int = 10, 
        use_hybrid: int = 1, 
        vector_weight: float = 0.6,
        reranker=None
    ):

        query_vector = None

        # 1. Get collection name
        collection_name = self.create_collection_name(project.project_id)

        # 2. Get query embedding
        vectors = self.embedding_client.embed_text(
            text=text,
            document_type=DocumentTypeEnum.QUERY.value
        )

        print(f"vectors: {len(vectors[0])}")

        if not vectors or len(vectors) == 0:
            return False

        if isinstance(vectors, list) and len(vectors) > 0:
            query_vector = vectors[0]

        if not query_vector:
            return False

        # IMPORTANT: retrieve more candidates for reranking
        retrieval_k = 60
        print(f"retrieval_k: {retrieval_k}")

        # 3. Perform search
        # 3. Perform search based on mode
        if use_hybrid==1:
            # Hybrid search (vector + BM25)
            print("use_hybrid")
            results = await self.vectordb_client.hybrid_search(
                collection_name=collection_name,
                query=text,
                vector=query_vector,
                vector_limit=limit * 2,  # Fetch more for reranking
                bm25_limit=limit * 2,     # Fetch more for reranking
                final_limit=limit,
            )
        elif use_hybrid==2:
            # Vector-only search
            results = await self.vectordb_client.search_by_vector(
                collection_name=collection_name,
                vector=query_vector,
                limit=limit
            )
        elif use_hybrid==3:
            results = await self.vectordb_client.search_by_bm25(
                collection_name=collection_name,
                query=text,
                limit=limit
            )

        # 4. RERANK STEP
        if results and len(results) > 0:

            pairs = [[text, r.text] for r in results]

            scores = self.reranker.predict(pairs)

            for r, score in zip(results, scores):
                r.rerank_score = float(score)

            results.sort(key=lambda x: x.rerank_score, reverse=True)

        # 5. Return best results
        return results[:limit]





    async def search_vectordb_collection_ranker(self, project: Project, text: str, limit: int = 10, 
                                        use_hybrid: bool = True, vector_weight: float = 0.9,
                                        use_reranker: bool = True):
        """
        Search vector database with optional Hybrid Search and Reranking.
        """
        collection_name = self.create_collection_name(project.project_id)
        
        # 1. Get text embedding vector
        vectors = self.embedding_client.embed_text(
            text=text,
            document_type=DocumentTypeEnum.QUERY.value
        )
        
        if not vectors or len(vectors) == 0:
            return []
        
        query_vector = vectors[0]

        # 2. Stage 1: Retrieval (Candidate Generation)
        # If reranking, we fetch more candidates (e.g., 25) to find the "hidden gems"
        retrieval_limit = limit * 14 if use_reranker else limit
        print(f"retrieval_limit: {retrieval_limit}")

        if use_hybrid:
            print(f"Performing Hybrid Search (Weight: {vector_weight})")
            initial_results = await self.vectordb_client.hybrid_search(
                collection_name=collection_name,
                query=text,
                vector=query_vector,
                vector_limit=retrieval_limit,
                bm25_limit=retrieval_limit,
                final_limit=retrieval_limit,
                vector_weight=vector_weight
            )
        else:
            print("Performing Vector-only Search")
            initial_results = await self.vectordb_client.search_by_vector(
                collection_name=collection_name,
                vector=query_vector,
                limit=retrieval_limit
            )

        if not initial_results:
            return []

        # 3. Stage 2: Reranking (Precision Refinement)
        if use_reranker and hasattr(self, 'ranker'):
            print(f"Reranking {len(initial_results)} candidates...")
            
            # Format candidates for FlashRank
            passages = [
                {"id": i, "text": doc.text, "meta": {"initial_score": doc.score}}
                for i, doc in enumerate(initial_results)
            ]
            
            rerank_request = RerankRequest(query=text, passages=passages)
            reranked_results = self.ranker.rerank(rerank_request)

            # Convert reranked results back to your Document format
            return [
                RetrievedDocument(
                    text=r['text'],
                    score=r['score'], # The new semantic relevance score
                )
                for r in reranked_results[:limit]
            ]

        # If no reranker, return top 'limit' from initial results
        return initial_results[:limit]



    async def search_vectordb_collection(self, project: Project, text: str, limit: int = 10, 
                                        use_hybrid: int=1):
        
        query_vector = None
        # 1. Get collection name
        collection_name = self.create_collection_name(project.project_id)
        
        # 2. Get text embedding vector
        vectors = self.embedding_client.embed_text(
            text=text,
            document_type=DocumentTypeEnum.QUERY.value
        )
        print(f"vectors: {len(vectors[0])}")
        
        if not vectors or len(vectors) == 0:
            return False
        
        if isinstance(vectors, list) and len(vectors) > 0:
            query_vector = vectors[0]

        if not query_vector:
            return False
        
        # 3. Perform search based on mode
        if use_hybrid==1:
            # Hybrid search (vector + BM25)
            print("use_hybrid")
            result = await self.vectordb_client.hybrid_search(
                collection_name=collection_name,
                query=text,
                vector=query_vector,
                vector_limit=limit * 2,  # Fetch more for reranking
                bm25_limit=limit * 2,     # Fetch more for reranking
                final_limit=limit,
            )
        elif use_hybrid==2:
            # Vector-only search
            result = await self.vectordb_client.search_by_vector(
                collection_name=collection_name,
                vector=query_vector,
                limit=limit
            )
        elif use_hybrid==3:
            result = await self.vectordb_client.search_by_bm25(
                collection_name=collection_name,
                query=text,
                limit=limit
            )
        
        return result
    


    async def answer_rag_question(self,project:Project, text:str, limit: int=10):
        answer, full_prompt,chat_history=None,None,None
        retrieved_doc=await self.search_vectordb_collection(
            project=project,
            text=text,
            limit=limit
        )

        system_prompt=self.templateLLM.get(
            "rag", "system_prompt"
        )

        docs_prompt='\n'.join([
            self.templateLLM.get(
                    "rag","document_prompt",{
                    "doc_num":ids+1,
                    "chunk_text": self.generation_client.process_text(doc.text)
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



    async def expand_rag_query(self, text:str):
        answer=None
        
        expand_prompt=self.templateLLM.get("rag","expand_prompt")
        chat_history=[
            self.generation_client.construct_prompt(
                prompt=expand_prompt,
                role=self.generation_client.enums.SYSTEM.value
            )
        ]
        answer=self.templateLLM.get("rag","expand_prompt",{"query":text})

        answer=self.expander.generate_text(
             prompt=answer,
             chat_history=chat_history
        )

        return answer