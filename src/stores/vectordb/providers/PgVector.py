
from ..VectorDBInterface import VectorDBInterface
from ..VectorDBbEnums import PgVectorIndexEnum, PgVectorDistanceMethodEnum, PgVectorTableEnums, VectorDBbEnums, DistanceMethodEnum
from models.schemas import RetrievedDocument
import logging
from typing import List
from sqlalchemy.sql import text as sql_text
import json
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
import asyncio


class PgVector(VectorDBInterface):

    def __init__(self, db_client, default_vector_size: int = 1024, distance_method: str= None, index_threshold:int= 100 ):
        self.db_client=db_client
        self.default_vector_size= default_vector_size
        if distance_method== DistanceMethodEnum.COSINE.value:
            distance_method=PgVectorDistanceMethodEnum.COSINE.value
        self.distance_method=distance_method
        self.pgvector_prefix= PgVectorTableEnums._PREFIX.value
        self.log= logging.getLogger('uvicorn')
        self.index_name= lambda collection_name: f"{collection_name}_vector_idx"
        self.index_threshold=index_threshold

    async def connect(self):
        async with self.db_client() as session:
            async with session.begin():
                await session.execute(sql_text(
                    "CREATE EXTENSION IF NOT EXISTS vector"
                ))
                await session.commit()


    def disconnect(self):
        pass



    async def is_collection_existed(self, collection_name: str)-> bool:
        rec= None
        async with self.db_client() as session:
            async with session.begin():
                list_tables=sql_text("SELECT * FROM pg_tables WHERE tablename = :collection_name")
                results= await session.execute(list_tables,{"collection_name":collection_name})
                rec= results.scalar_one_or_none()
        return rec


    async def list_all_collections(self, collection_name: str)-> List:
        rec= []
        async with self.db_client() as session:
            async with session.begin():
                list_tables=sql_text("SELECT tablename FROM pg_tables WHERE tablename like :prefix")
                results= await session.execute(list_tables, {"prefix":self.pgvector_prefix})
                rec= results.scalar().all()
        return rec


    async def get_collection_info(self, collection_name: str) -> dict:
        async with self.db_client() as session:
            async with session.begin():
                table_info=sql_text(
                    '''
                    SELECT schemaname, tablename, tableowner, tablespace, hasindexes
                    FROM pg_tables
                    where tablename = :collection_name
                    '''
                )
                count=sql_text(f"select count(*) from {collection_name}")
                results= await session.execute(table_info,{"collection_name": collection_name})
                count=await session.execute(count)
                table_data=results.fetchone()
                if not table_data:
                    return None
                else:
                    return {
                        "table_data": {
                            "schemaname": table_data[0],
                            "tablename":   table_data[1] ,
                            "tableowner": table_data[2],
                            "tablespace": table_data[3],
                            "hasindexes":table_data[4]
                        },
                        "count_inserted": count.scalar_one()
                    }


    async def delete_collection(self, collection_name: str):
        async with self.db_client() as session:
            async with session.begin():
                deleted_table=sql_text(
                    f"DROP TABLE IF EXISTS {collection_name}"
                )
                await session.execute(deleted_table)
                session.commit()
        return True


    async def create_collection(self, collection_name: str,
                                embedding_size: int,
                                do_reset:int=False):
        if do_reset:
            await self.delete_collection(collection_name)
        
        is_collection_existed=await self.is_collection_existed(collection_name)

        if not is_collection_existed:
            self.log.info(f"creating collection: {collection_name}")
            async with self.db_client() as session:
                async with session.begin():
                    create_table=sql_text(
                        f'CREATE TABLE {collection_name} ('
                        f'{PgVectorTableEnums.ID.value} bigserial PRIMARY KEY, '
                        f'{PgVectorTableEnums.TEXT.value} text, '
                        f'{PgVectorTableEnums.VECTOR.value} vector({embedding_size}), '
                        f'{PgVectorTableEnums.METADATA.value} jsonb DEFAULT \'{{}}\', '
                        f'{PgVectorTableEnums.CHUNK_ID.value} integer, '
                        f'FOREIGN KEY ({PgVectorTableEnums.CHUNK_ID.value}) REFERENCES chunks(chunk_id)'
                        ')'
                    )
                    await session.execute(create_table)
                    await session.commit()
            return True
        return False


    async def is_index_existed(self, collection_name:str)-> bool:
        index_name=self.index_name(collection_name)
        async with self.db_client() as session:
                async with session.begin(): 
                    check=sql_text(
                        f"""
                        SELECT 1  FROM pg_indexes  WHERE tablename = {collection_name} AND indexname = :index_name
                        """
                    )
                    results=await session.execute(check,{"index_name":index_name})
                    return bool(results.scalar_one_or_none())
    

    async def create_index(self, collection_name: str, index_type: str=PgVectorIndexEnum.HNSW.value):
        is_index_existed=await self.is_index_existed(collection_name)
        if not is_index_existed:
            self.log.info(f"There are no indexes")
            return False
        async with self.db_client() as session:
                async with session.begin():
                    count=sql_text(
                        f"SELECT COUNT(*) FROM {collection_name}"
                    )
                    result=await session.execute(count)
                    records = result.scalar_one()
                    if records < self.index_threshold:
                        return False
                    self.log.info(f"Creating index")
                    index_name=self.index_name(collection_name)
                    index_sql=sql_text(
                        f"CREATE INDEX {index_name} ON {collection_name} "
                        f"USING {index_type} ({PgVectorTableEnums.VECTOR.value} {self.distance_method})"
                    )
                    await session.execute(index_sql)
                    session.commit()
                    self.log.info(f"index Created")

    
    async def reset_vector_index(self, collection_name:str, index_type: str= PgVectorIndexEnum.HNSW.value):
        index_name=self.index_name(collection_name)
        async with self.db_client() as session:
                async with session.begin():
                    drop_index=sql_text(
                        f"DROP INDEX IF EXISTS {index_name}"
                    )
                    await session.execute(drop_index)
        return await self.create_index(collection_name=collection_name, index_type=index_type)



    async def insert_one(self,collection_name: str, text: str, vector: list, metadata: dict, record_id: str= None ):
        is_collection_existed=await self.is_collection_existed(collection_name)

        if not is_collection_existed:
            self.log.info(f"There is no collection: {collection_name}")
            return False

        if not record_id:
            self.log.info(f"Can't insert record without chunk_id")
            return False
        
        async with self.db_client() as session:
                async with session.begin():
                    insert_value=sql_text(
                        f'INSERT INTO {collection_name} '
                        f'({PgVectorTableEnums.TEXT.value}, {PgVectorTableEnums.VECTOR.value}, {PgVectorTableEnums.METADATA.value}, {PgVectorTableEnums.CHUNK_ID.value}) '
                        'VALUES (:text, :vector, :metadata, :record_id)'
                    )
                    meta_json=json.dumps(metadata, ensure_ascii=False) if not None else "{}"
                    await session.execute(insert_value,{
                        "text":text,
                        "vector":"[" +",".join([str(v) for v in vector]) + "]", 
                        "metadata": meta_json, 
                        "record_id":record_id 
                        })
                    await session.commit()
        return True


    async def insert_many(self,collection_name: str, texts: list, vectors: list, metadata: list= None, record_ids: list= None, batch_size: int=50):
        is_collection_existed=await self.is_collection_existed(collection_name)

        if not is_collection_existed:
            self.log.info(f"There is no collection: {collection_name}")
            return False
        if len(vectors)!= len(record_ids):
            self.log.info(f"invalid insertion")
            return False
        
        if not metadata or len(metadata)==0:
            metadata=[None] *len(texts)
        
        async with self.db_client() as session:
                async with session.begin():
                    for i in range(0, len(texts), batch_size):
                        batch_texts=texts[i:i+batch_size]
                        batch_vectors=vectors[i:i+batch_size]
                        batch_record_ids=record_ids[i:i+batch_size]
                        batch_metadata=metadata[i:i+batch_size]
                        values=[]
                        for te, vec, rec, meta in zip(batch_texts,batch_vectors,batch_record_ids,batch_metadata):
                            meta_json=json.dumps(meta, ensure_ascii=False) if not None else "{}"
                            values.append({
                                "text":te,
                                "vector":"[" +",".join([str(v) for v in vec]) + "]", 
                                "metadata": meta_json, 
                                "record_id":rec 
                            })
                        batch_insert=sql_text(
                            f'INSERT INTO {collection_name} '
                        f'({PgVectorTableEnums.TEXT.value}, {PgVectorTableEnums.VECTOR.value}, {PgVectorTableEnums.METADATA.value}, {PgVectorTableEnums.CHUNK_ID.value}) '
                        ' VALUES ( :text, :vector, :metadata, :record_id )'
                        )
                        await session.execute(batch_insert,values)
                        await session.commit()
        return True


    async def search_by_vector(self,collection_name: str, vector: list, limit: int ):
        is_collection_existed=await self.is_collection_existed(collection_name)

        if not is_collection_existed:
            self.log.info(f"There is no collection: {collection_name} to search")
            return False
        if len(vector) > 0 and isinstance(vector[0], list):
            vector = vector[0]

        vector = "[" + ",".join([ str(v) for v in vector ]) + "]"
        async with self.db_client() as session:
                    search_vector=sql_text(
                        f'SELECT {PgVectorTableEnums.TEXT.value} as text, 1-  ({PgVectorTableEnums.VECTOR.value} <=> :vector) as score '
                        f' FROM {collection_name} '
                        f' ORDER BY score DESC '
                        f' LIMIT :limit '
                    )
                    results=await session.execute(search_vector, {"vector":vector,"limit":limit})
                    records=results.fetchall()

                    return [
                        RetrievedDocument(
                        text= rec.text,
                        score= rec.score
                    )
                        for rec in records
                    ]
                
    
    
    async def search_by_text(self, collection_name: str, query: str, limit: int = 8):
        is_collection_existed = await self.is_collection_existed(collection_name)
        
        if not is_collection_existed:
            self.log.info(f"There is no collection: {collection_name} to search")
            return []
        
        formatted_query = f"%{query.strip()}%"
        async with self.db_client() as session:
            self.log.info(f"Running Keyword Search for: {query}")
            
            # Using ILIKE for case-insensitive text search
            search_query = sql_text(
                f'SELECT {PgVectorTableEnums.TEXT.value} as text, 1.0 as score '
                f'FROM {collection_name} '
                f'WHERE {PgVectorTableEnums.TEXT.value} ILIKE :query_text '
                f'ORDER BY {PgVectorTableEnums.ID.value} DESC '
                f'LIMIT :limit'
            )
            
            results = await session.execute(search_query, {
                "query_text": formatted_query, 
                "limit": limit
            })
            records = results.fetchall()
            
            return [
                RetrievedDocument(
                    text=rec.text,
                    score=float(rec.score)
                )
                for rec in records
            ]







    async def hybrid_search(self, collection_name: str, vector: list, query: str, bm25_limit: int,vector_limit:int, final_limit:int, k: int = 60):
        is_collection_existed = await self.is_collection_existed(collection_name)
        if not is_collection_existed:
            self.log.info(f"There is no collection: {collection_name} to search")
            return False

        # Flatten vector if nested
        if len(vector) > 0 and isinstance(vector[0], list):
            vector = vector[0]
        vector = "[" + ",".join([str(v) for v in vector]) + "]"

        # Sanitize FTS query: join words with & for tsquery
        fts_query = " & ".join(query.strip().split())

        async with self.db_client() as session:
            search_query = sql_text(
                f"""
                WITH vector_search AS (
                    SELECT {PgVectorTableEnums.TEXT.value} as text,
                        ROW_NUMBER() OVER (
                            ORDER BY {PgVectorTableEnums.VECTOR.value} <=> :vector
                        ) AS rank
                    FROM {collection_name}
                    ORDER BY {PgVectorTableEnums.VECTOR.value} <=> :vector
                    LIMIT 50
                ),
                keyword_search AS (
                    SELECT {PgVectorTableEnums.TEXT.value} as text,
                        ROW_NUMBER() OVER (
                            ORDER BY ts_rank_cd(
                                to_tsvector('english', {PgVectorTableEnums.TEXT.value}),
                                to_tsquery('english', :fts_query)
                            ) DESC
                        ) AS rank
                    FROM {collection_name}
                    WHERE to_tsvector('english', {PgVectorTableEnums.TEXT.value})
                        @@ to_tsquery('english', :fts_query)
                    LIMIT 50
                )
                SELECT
                    COALESCE(vs.text, ks.text) AS text,
                    COALESCE(1.0 / (:k + vs.rank), 0) +
                    COALESCE(1.0 / (:k + ks.rank), 0) AS score
                FROM vector_search vs
                FULL OUTER JOIN keyword_search ks ON vs.text = ks.text
                ORDER BY score DESC
                LIMIT :limit
                """
            )

            results = await session.execute(search_query, {
                "vector": vector,
                "fts_query": fts_query,
                "k": k,
                "limit": bm25_limit
            })
            records = results.fetchall()

            return [
                RetrievedDocument(
                    text=rec.text,
                    score=rec.score
                )
                for rec in records
            ]