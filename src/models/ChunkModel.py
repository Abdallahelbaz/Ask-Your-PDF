from .BaseData import BaseData
from .schemas import Chunk
from .enums.DatabaseEnum import DatabaseEnum
from bson.objectid import ObjectId
from pymongo import InsertOne
import logging

class ChunkModel(BaseData):
    def __init__(self,client: object ):
        super().__init__(client)
        self.collection= self.client[DatabaseEnum.COLLECTION_CHUNKS.value]
    

    @classmethod
    async def create_instance(cls, client: object):
        instance = cls(client)
        await instance.init_collection()
        return instance

    async def init_collection(self):
        all_coll= await self.client.list_collection_names()
        if DatabaseEnum.COLLECTION_CHUNKS.value not in all_coll:
            self.collection= self.client[DatabaseEnum.COLLECTION_CHUNKS.value]
            indexes= Chunk.get_indexes()
            for index in indexes:
                await self.collection.create_index(
                    index["key"],
                    name= index["name"],
                    unique=index["unique"]
                )


    async def create_chunk(self, chunk: Chunk):
        # model_dump() to convert data to dict
        inserted_chunk= self.collection.insert_one(chunk.model_dump(by_alias=True, exclude_unset=True))
        chunk.id= inserted_chunk.inserted_id


        return chunk

    async def get_chunk(self, chunk_id: str):
        record= await self.collection.find_one({
            "id": ObjectId(chunk_id)
        })

        if record is None: 
            return None
        
        return Chunk(**record)


    # if we have too many chunks, and we inserted it as a one batch, may it causes a problem with the data base
    # so insert them batch by batch
    async def insert_many(self, chunks: list, batch: int =100):

        for i in range(0, len(chunks), batch):
            batch= chunks [i: i + batch]

            operations=[
                InsertOne(chunk.model_dump(by_alias=True, exclude_unset=True))
                for chunk in batch
            ]
            # it inserts the bulk(batch) i made, it's better than insert many
            await self.collection.bulk_write(operations)
        
        return len(chunks)
    

    async def delete_chunks_by_project_id(self, project_id: ObjectId):
        result= await self.collection.delete_many({
            "chunk_project_id": project_id
        })

        return result.deleted_count