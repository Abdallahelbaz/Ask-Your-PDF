from ..VectorDBInterface import VectorDBInterface
from ..VectorDBbEnums import DistanceMethodEnum
from qdrant_client import models, QdrantClient
import logging
from typing import List
from models.schemas.Chunk import RetrievedDocument
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from typing import List, Optional, Dict, Any
import asyncio

class QdrantDB(VectorDBInterface):
    def __init__(self,db_path: str, distance_method: str):
        self.db_path=db_path
        self.distance_method= None
        self.client= None
        self.log=logging.getLogger(__name__)
        
        if distance_method== DistanceMethodEnum.COSINE.value:
            self.distance_method= models.Distance.COSINE
        elif distance_method== DistanceMethodEnum.DOT.value:
            self.distance_method= models.Distance.DOT
        


        self.log=logging.getLogger(__name__)
    
    def connect(self):
        self.client=QdrantClient(path=self.db_path)


    def disconnect(self):
        self.client=None
        raise NotImplementedError


    def is_collection_existed(self, collection_name: str)-> bool:
        return self.client.collection_exists(collection_name=collection_name)


    def list_all_collections(self, collection_name: str)-> List:
        return self.client.get_collections()


    async def get_collection_info(self, collection_name: str) -> dict:
        return self.client.get_collection(collection_name=collection_name)


    def delete_collection(self, collection_name: str):
        if self.is_collection_existed(collection_name):
            return self.client.delete_collection(collection_name=collection_name)
        


    # def create_collection(self, collection_name: str,
    #                             embedding_size: int,
    #                             do_reset:int=False):
    #     if do_reset:
    #         self.delete_collection(collection_name=collection_name)
        
    #     if not self.is_collection_existed(collection_name=collection_name):
    #         self.client.create_collection(
    #         collection_name=collection_name,
    #         vectors_config=models.VectorParams(
    #                         size=embedding_size, 
    #                         distance=self.distance_method
    #             )
    #         )
    #         return True
    #     return False


    async def create_collection(self, collection_name: str, 
                                embedding_size: int,
                                do_reset: bool = False):
        if do_reset:
            _ = self.delete_collection(collection_name=collection_name)
        
        if not self.is_collection_existed(collection_name):
            self.log.info(f"Creating new Qdrant collection: {collection_name}")
            
            _ = self.client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=embedding_size,
                    distance=self.distance_method
                )
            )

            return True
        
        return False


    def insert_one(self,collection_name: str, text: str, vector: list, metadata: dict, record_id: str= None ):
        if not self.is_collection_existed(collection_name=collection_name):
            self.log.error("Collection is Not Existed")
            return False
        self.client.upload_points(
            collection_name=collection_name,
            records=[
                models.Record(
                    id=[record_id],
                    vector=vector,
                    payload={
                        "text": text,
                        "metadata": metadata
                    }
                )
            ]
        )
        return True


    async def insert_many(self, collection_name: str, texts: list, 
                        vectors: list, metadata: list = None, 
                        record_ids: list = None, batch_size: int = 50):
        
        if metadata is None:
            metadata = [None] * len(texts)

        if record_ids is None:
            record_ids = list(range(0, len(texts)))

        for i in range(0, len(texts), batch_size):
            batch_end = i + batch_size

            batch_texts = texts[i:batch_end]
            batch_vectors = vectors[i:batch_end]
            batch_metadata = metadata[i:batch_end]
            batch_record_ids = record_ids[i:batch_end]

            batch_records = [
                models.Record(
                    id=batch_record_ids[x],
                    vector=batch_vectors[x],
                    payload={
                        "text": batch_texts[x], "metadata": batch_metadata[x]
                    }
                )

                for x in range(len(batch_texts))
            ]

            try:
                _ = self.client.upload_points(
                    collection_name=collection_name,
                    points=batch_records,
                )
            except Exception as e:
                self.log.error(f"Error while inserting batch: {e}")
                return False

        return True


    def get_collection(self, collection_name: str):
        """
        Returns Qdrant collection info (schema, vectors, points count, etc.)
        """
        return self.client.get_collection(collection_name=collection_name)
    

    async def search_by_vector(self,collection_name: str, vector: list, limit: int=8 ):
        points=self.client.query_points(
            collection_name= collection_name,
            query=vector,
            limit=limit,
        )
        
        if not points:
            return None

        # i want to return specific data, not all data, so i wont use only return anymore
        # return points
        return [
            RetrievedDocument(
                score= p.score,
                text= p.payload.get("text","")
            )
            for p in points.points
        ]
    

    async def search_by_bm25(self, collection_name: str, query: str, limit: int = 8):
        """
        Search using BM25 algorithm (keyword-based)
        """
        # First, get all documents from the collection to create BM25 index
        all_points = self.client.scroll(
            collection_name=collection_name,
            limit=10000,  # Adjust based on your collection size
            with_payload=True,
        )
        
        if not all_points or not all_points[0]:
            return []
        
        # Convert to LangChain Documents for BM25
        documents = []
        for point in all_points[0]:
            doc = Document(
                page_content=point.payload.get("text", ""),
                metadata={k: v for k, v in point.payload.items() if k != "text"}
            )
            documents.append(doc)
        
        # Create BM25 retriever
        bm25_retriever = BM25Retriever.from_documents(documents)
        bm25_retriever.k = limit
        
        # OPTION 1: Use invoke() for newer LangChain versions
        try:
            # Try the new method first
            results = bm25_retriever.invoke(query)
        except AttributeError:
            try:
                # Fall back to the old method
                results = bm25_retriever.get_relevant_documents(query)
            except AttributeError:
                # Try the async method
                results = await bm25_retriever.ainvoke(query)
        
        return [
            RetrievedDocument(
                score=1.0 - (i / len(results)) if results else 0,
                text=doc.page_content,
                metadata=doc.metadata
            )
            for i, doc in enumerate(results)
        ]



    async def hybrid_search(self, collection_name: str, query: str, vector: list, 
                           vector_limit: int = 8, bm25_limit: int = 8, 
                           final_limit: int = 8, vector_weight: float = 0.5):
        """
        Perform hybrid search combining vector and BM25 results
        """
        # Run both searches in parallel
        vector_task = self.search_by_vector(collection_name, vector, vector_limit)
        bm25_task = self.search_by_bm25(collection_name, query, bm25_limit)
        
        vector_results, bm25_results = await asyncio.gather(vector_task, bm25_task)
        
        # Combine and deduplicate results
        combined = {}
        
        # Add vector results with weighted scores
        for doc in vector_results:
            key = doc.text[:100]  # Use text prefix as key for deduplication
            if key not in combined:
                combined[key] = {
                    'text': doc.text,
                    'metadata': doc.metadata,
                    'vector_score': doc.score,
                    'bm25_score': 0,
                    'count': 1
                }
            else:
                combined[key]['vector_score'] = max(combined[key]['vector_score'], doc.score)
        
        # Add BM25 results with weighted scores
        for doc in bm25_results:
            key = doc.text[:100]
            if key not in combined:
                combined[key] = {
                    'text': doc.text,
                    'metadata': doc.metadata,
                    'vector_score': 0,
                    'bm25_score': doc.score,
                    'count': 1
                }
            else:
                combined[key]['bm25_score'] = max(combined[key]['bm25_score'], doc.score)
                combined[key]['count'] += 1
        
        # Calculate hybrid scores
        hybrid_results = []
        for key, data in combined.items():
            # Normalize scores if needed (assumes scores are in similar ranges)
            hybrid_score = (vector_weight * data['vector_score'] + 
                          (1 - vector_weight) * data['bm25_score'])
            
            # Boost score if document appears in both result sets
            if data['count'] > 1:
                hybrid_score *= 1.1  # 10% boost for overlapping results
            
            hybrid_results.append({
                'score': hybrid_score,
                'text': data['text'],
                'metadata': data['metadata'],
                'vector_score': data['vector_score'],
                'bm25_score': data['bm25_score']
            })
        
        # Sort by hybrid score and limit results
        hybrid_results.sort(key=lambda x: x['score'], reverse=True)
        hybrid_results = hybrid_results[:final_limit]
        
        return [
            RetrievedDocument(
                score=item['score'],
                text=item['text'],
                metadata=item['metadata']
            )
            for item in hybrid_results
        ]