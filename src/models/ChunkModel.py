from .BaseData import BaseData
from .schemas import Chunk
from .enums.DatabaseEnum import DatabaseEnum
import logging
from sqlalchemy.future import select
from sqlalchemy import func, delete, and_
from bson import ObjectId
from typing import List, Optional, Dict, Any


class ChunkModel(BaseData):
    def __init__(self, client: object):
        super().__init__(client)
        self.client = client
    

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
    
    async def get_chunk(self, chunk_id: int):  
        async with self.client() as session:
            result = await session.execute(select(Chunk).where(Chunk.chunk_id == chunk_id))
            chunk = result.scalar_one_or_none()
        return chunk
    
    async def insert_many(self, chunks: list, batch_size: int = 100):
        async with self.client() as session:
            async with session.begin():
                for i in range(0, len(chunks), batch_size):
                    batch = chunks[i:i+batch_size]
                    session.add_all(batch)
            await session.commit()        
        return len(chunks)
    
    async def delete_chunks_by_project_id(self, project_id: int):  
        async with self.client() as session:
            query = delete(Chunk).where(Chunk.chunk_project_id == project_id)
            result = await session.execute(query)
            await session.commit()
        return result.rowcount
    
    async def get_parent_chunk(self, parent_id: str,project_id: int,):
        async with self.client() as session:
            async with session.begin():
                query = select(Chunk).where(Chunk.chunk_project_id == project_id).where(Chunk.chunk_id==parent_id)
                result = await session.execute(query)
                chunk = result.scalar_one_or_none()
            return chunk

    async def get_project_chunks_base(self, project_id: int, page_no: int = 1, page_size: int = 50):
        async with self.client() as session:
            async with session.begin():
                query = select(Chunk).where(Chunk.chunk_project_id == project_id).offset((page_no - 1) * page_size).limit(page_size)
                result = await session.execute(query)
                chunks = result.scalars().all()
        return chunks

    async def get_project_chunks(self, project_id: int, page_no: int = 1, page_size: int = 50):
        async with self.client() as session:

            query = (
                select(Chunk)
                .where(Chunk.chunk_project_id == project_id)
                .where(Chunk.parent_id.is_not(None))  
                .offset((page_no - 1) * page_size)
                .limit(page_size)
            )
            result = await session.execute(query)
            chunks = result.scalars().all()
            
        return chunks

    
    async def get_total_chunks_count(self, project_id: int):
        count = 0
        async with self.client() as session:    
            # Adding the filter for child chunks only
            query = (
                select(func.count(Chunk.chunk_id))
                .where(Chunk.chunk_project_id == project_id)
                .where(Chunk.parent_id.is_not(None)) 
            )
            
            result = await session.execute(query)
            count = result.scalar()
            
        return count
    

    async def insert_parent_child_chunks(self, child_data_list: list, parent_chunks: list):
        all_child_objs = []
        async with self.client() as session:
            async with session.begin():
                # 1. Add parents and flush to get their database IDs
                session.add_all(parent_chunks)
                await session.flush()

                for i, parent_obj in enumerate(parent_chunks):

                    if i < len(child_data_list):
                        children_for_this_parent = child_data_list[i]
                        
                        for child_data in children_for_this_parent:

                            child_data.parent_id = parent_obj.chunk_id
                            

                            all_child_objs.append(child_data)


                session.add_all(all_child_objs)
                

                await session.flush()

                for child in all_child_objs:
                    await session.refresh(child)
                        
        return all_child_objs


