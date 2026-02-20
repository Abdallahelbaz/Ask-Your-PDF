from pydantic import BaseModel, Field
from typing import Optional
from bson.objectid import ObjectId

class Chunk(BaseModel):
    id: Optional[ObjectId]=Field(default=None, alias="_id")
    chunk_text: str= Field(..., min_length=1)
    chunk_metadata: dict
    chunk_project_id: ObjectId
    # greater than
    chunk_order: int= Field(..., gt=0)

    class Config:
        arbitrary_types_allowed=True
    
    @classmethod
    def get_indexes(cls):
        return [
            {
                "key":[
                    ("chunk_project_id",1)
                ],
                "name": "chunk_project_id_index_1",
                "unique": False
            }
        ]