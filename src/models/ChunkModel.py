from .BaseData import BaseData
from .schemas import Chunk
from .enums.DatabaseEnum import DatabaseEnum
import logging
from sqlalchemy.future import select
from sqlalchemy import func, delete
from bson import ObjectId


class ChunkModel(BaseData):
    def __init__(self,client: object ):
        super().__init__(client)
        self.client= client
    

    @classmethod
    async def create_instance(cls, client: object):
        instance = cls(client)
        return instance

    async def create_chunk(self, chunk: Chunk):
        async with self.client() as session:
            async with session.begin():
                session.add(chunk)
            await session.commit()
            await session.refresh(chunk)
        return chunk
    

    async def get_chunk(self, chunk_id: str):
        async with self.client() as session:
            result=await session.excute(select(Chunk).where(Chunk.chunk_id==chunk_id))
            chunk= result.scalar_one_or_none()
        return chunk
                           


    # if we have too many chunks, and we inserted it as a one batch, may it causes a problem with the data base
    # so insert them batch by batch
    async def insert_many(self, chunks: list, batch_size: int =100):
        async with self.client() as session:
            async with session.begin():
                for i in range(0, len(chunks), batch_size):
                    batch= chunks[i:i+batch_size]
                    session.add_all(batch)
            await session.commit()        
        return len(chunks)
    

    async def delete_chunks_by_project_id(self, project_id: ObjectId):
        async with self.client() as session:
            result=await session.execute(delete(Chunk).where(Chunk.chunk_project_id==project_id))
            await session.commit()
        return result.rowcount
    
    async def get_project_chunks(self,project_id: ObjectId, page_no: int=1, page_size:int=50):
        async with self.client() as session:
            async with session.begin():
                query= select(Chunk).where(Chunk.chunk_project_id==project_id).offset((page_no - 1 ) * page_size).limit(page_size)
                result= await session.execute(query)
                chunks=result.scalars().all()
        return chunks