from .BaseController import BaseController
from models.schemas import Project, Chunk
from models.ChunkModel import ChunkModel
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


    async def search_vectordb_collection(
        self, 
        project: Project, 
        text: str, 
        limit: int = 10, 
        use_hybrid: int =1, 
        vector_weight: float = 0.6,
        reranker=None,
        client=None
    ):
        
        # expanded_text=await self.expand_rag_query(text)
        query_vector = None

        print(f"the query is: {text}")
        # 1. Get collection name
        collection_name = self.create_collection_name(project.project_id)
        chunk_model= await ChunkModel.create_instance(
        client=client
        )
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
                final_limit=50,
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
                limit=50
            )

        # # 4. RERANK STEP
        if results and len(results) > 0:

            pairs = [[text, r.text] for r in results]

            scores = self.reranker.predict(pairs)

            for r, score in zip(results, scores):
                r.rerank_score = float(score)

            results.sort(key=lambda x: x.rerank_score, reverse=True)
        #     print(len(results))
        
        # return results[:limit]

        parents=[]
        docs=[]
        for parent in results[:limit]:
            parent_id=parent.metadata.get('parent_id')
            parent_chunk=await chunk_model.get_parent_chunk(parent_id, project.project_id)
            parents.append(parent_chunk)
            doc=RetrievedDocument(
                        score=parent.score,
                        text=parent_chunk.chunk_text,
                        rerank_socre=parent.rerank_score,
                        source="hybrid_rrf_qdrant",
                    )
            docs.append(doc)

        # return results[:limit]

        return docs



    async def answer_rag_question(self,project:Project, text:str, limit: int=10, client=None):
            answer, full_prompt,chat_history=None,None,None

            # expanded_text=await self.expand_rag_query(text)

            retrieved_doc=await self.search_vectordb_collection(
                project=project,
                text=text,
                limit=limit,
                client=client
            )

            print(retrieved_doc)
            system_prompt=self.templateLLM.get(
                "rag", "system_prompt"
            )

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





    async def expand_rag_query(self, text:str):
        answer=None
        
        expand_prompt=self.templateLLM.get("rag","expand_prompt")
        print(expand_prompt,"\n")

        
        print(expand_prompt)
        chat_history=[
            self.generation_client.construct_prompt(
                prompt=expand_prompt,
                role=self.generation_client.enums.SYSTEM.value
            )
        ]

        answer=self.templateLLM.get("rag","answer",{"query":text})
        print("\n",answer,'\n chat History: \n', chat_history)
        answer=self.expander.generate_text(
             prompt=answer,
             chat_history=chat_history
        )
        print("\n",answer)
        return answer