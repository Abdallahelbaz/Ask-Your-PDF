from ..VectorDBInterface import VectorDBInterface
from ..VectorDBbEnums import DistanceMethodEnum
from qdrant_client import models, QdrantClient
import logging
from typing import List
from models.schemas import RetrievedDocument
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from typing import List, Optional, Dict, Any
import asyncio
import re
from collections import defaultdict
from fastembed import SparseTextEmbedding

class QdrantDB(VectorDBInterface):
    def __init__(self,db_path: str, distance_method: str):
        self.db_path=db_path
        self.distance_method= None
        self.client= None
        self.log=logging.getLogger("uvicorn")
        self.sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")
        if distance_method== DistanceMethodEnum.COSINE.value:
            self.distance_method= models.Distance.COSINE
        elif distance_method== DistanceMethodEnum.DOT.value:
            self.distance_method= models.Distance.DOT
        


        
    
    async def connect(self):
        self.client=QdrantClient(path=self.db_path)


    async def disconnect(self):
        self.client=None
        raise NotImplementedError


    async def is_collection_existed(self, collection_name: str)-> bool:
        return self.client.collection_exists(collection_name=collection_name)


    async def list_all_collections(self, collection_name: str)-> List:
        return self.client.get_collections()


    async def get_collection_info(self, collection_name: str) -> dict:
        return self.client.get_collection(collection_name=collection_name)


    async def delete_collection(self, collection_name: str):
        if await self.is_collection_existed(collection_name):
            return self.client.delete_collection(collection_name=collection_name)
        


    async def create_collection(self, collection_name: str,
                                    embedding_size: int,
                                    do_reset: bool = False):
        if do_reset:
            print(f"Deleting collection: {collection_name}")
            await self.delete_collection(collection_name=collection_name)
        
        if not await self.is_collection_existed(collection_name=collection_name):
            # Using the async client to create the collection
            self.client.create_collection(
                collection_name=collection_name,
                # Pass a dictionary to give the dense vector a specific name
                vectors_config={
                    "text-dense": models.VectorParams(
                        size=embedding_size, 
                        distance=self.distance_method
                    )
                },
                sparse_vectors_config={
                    "bm25": models.SparseVectorParams(
                        modifier=models.Modifier.IDF
                    )
                }
            )
            print(f"Created collection: {collection_name} with BM25 support")
            return True
        return False


    async def insert_one(self,collection_name: str, text: str, vector: list, metadata: dict, record_id: str= None ):
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

    async def insert_many_json(
        self,
        collection_name: str,
        texts: list,
        vectors: list,
        metadata: list = None,
        record_ids: list = None,
        batch_size: int = 50
    ):

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

            batch_records = []

            for x in range(len(batch_texts)):

                meta = batch_metadata[x] or {}

                paragraph = meta.get("paragraph", "")
                keywords = meta.get("key_words", [])
                title = meta.get("title", "")

                if keywords is None:
                    keywords = []

                sparse_text = f"{paragraph} {title} {' '.join(keywords)}".strip()
                print("Sparse text:", sparse_text)
                point = models.PointStruct(
                    id=batch_record_ids[x],

                    vector={
                        "dense": batch_vectors[x],

                        "sparse": models.Document(
                            text=sparse_text,
                            model="qdrant/bm25"
                        )
                    },

                    payload={
                        "text": batch_texts[x],
                        "metadata": meta
                    }
                )

                batch_records.append(point)

            try:
                _ = self.client.upload_points(
                    collection_name=collection_name,
                    points=batch_records
                )

            except Exception as e:
                self.log.error(f"Error while inserting batch at index {i}: {e}")
                return False

        return True
    


    async def insert_many(self, collection_name: str, texts: list, 
                        vectors: list, metadata: list = None, 
                        record_ids: list = None, batch_size: int = 50):
        
        if metadata is None:
            metadata = [{}] * len(texts)

        if record_ids is None:
            record_ids = list(range(0, len(texts)))

        sparse_vectors = list(self.sparse_model.embed(texts))

        for i in range(0, len(texts), batch_size):
            batch_end = i + batch_size

            batch_texts = texts[i:batch_end]
            batch_vectors = vectors[i:batch_end] 
            batch_sparse = sparse_vectors[i:batch_end]
            batch_metadata = metadata[i:batch_end]
            batch_record_ids = record_ids[i:batch_end]

            batch_points = [
                models.PointStruct(  
                    id=batch_record_ids[x],
                    vector={
                        "text-dense": batch_vectors[x], 
                        "bm25": batch_sparse[x].as_object() 
                    },
                    payload={
                        "text": batch_texts[x], 
                        "metadata": batch_metadata[x]
                    }
                )
                for x in range(len(batch_texts))
            ]

            try:
                # Using the client to upload points
                self.client.upload_points(
                    collection_name=collection_name,
                    points=batch_points,
                    wait=True
                )
            except Exception as e:
                print(f"Error while inserting batch: {e}")
                return False

        return True



    async def get_collection(self, collection_name: str):
        """
        Returns Qdrant collection info (schema, vectors, points count, etc.)
        """
        return self.client.get_collection(collection_name=collection_name)
    

    
    async def search_by_vector(self,collection_name: str, vector: list, limit: int=8 ):
        points=self.client.query_points(
            collection_name= collection_name,
            query=vector,
            limit=limit,
            using="text-dense",
            # score_threshold=0.5
        )
        
        if not points:
            return None

        return [
            RetrievedDocument(
                score= p.score,
                text= p.payload.get("text",""), 
                metadata=p.payload.get("metadata",{}),
                source="Vector_search"
            )
            for p in points.points
        ]


    async def search_by_bm25(
        self,
        collection_name: str,
        query: str,
        limit: int = 8
    ):

        print("BM25 query:", query, "\n")

        try:
            points = self.client.query_points(
                collection_name=collection_name,
                query=models.Document(
                    text=query,
                    model="qdrant/bm25"
                ),
                using="bm25",
                limit=limit,
                # score_threshold=0.7,
                with_payload=True,
                with_vectors=False
            )

            if not points or not points.points:
                return []

            return [
                RetrievedDocument(
                    score=p.score,
                    text=p.payload.get("text", ""),
                    metadata=p.payload.get("metadata", {}),
                    source="search_by_bm25"
                )
                for p in points.points
            ]

        except Exception as e:
            print(f"BM25 search error: {e}")
            return []



    async def hybrid_search(
        self,
        collection_name: str,
        query: str,
        vector: list,
        vector_limit: int = 20,
        bm25_limit: int = 20,
        final_limit: int = 10,
        rank_constant: int = 60
    ):

        print("Hybrid query:", query, "\n")

        try:
            points = self.client.query_points(
                collection_name=collection_name,

                # prefetch both searches
                prefetch=[
                    models.Prefetch(
                        query=vector,
                        using="text-dense",
                        limit=500,
                        # score_threshold=0.5
                    ),
                    models.Prefetch(
                        query=models.Document(
                            text=query,
                            model="qdrant/bm25"
                        ),
                        using="bm25",
                        limit=500,
                        # score_threshold=0.5
                    )
                ],

                # built-in RRF
                query=models.FusionQuery(
                    fusion=models.Fusion.RRF ),

                limit=100,
                with_payload=True,
                with_vectors=False
            )

            if not points or not points.points:
                return []

            return [
                RetrievedDocument(
                    score=p.score,
                    text=p.payload.get("text", ""),
                    metadata=p.payload.get("metadata", {}),
                    source="hybrid_rrf_qdrant",
                    order=i,
                    parent_id=p.payload.get("metadata", {}).get("parent_id")
                )
                for i, p in enumerate(points.points, start=1)
            ]

        except Exception as e:
            print(f"Hybrid search error: {e}")
            return []

    