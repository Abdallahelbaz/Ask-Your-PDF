from pydantic import BaseModel, Field
from typing import Optional
from bson.objectid import ObjectId

class Project(BaseModel):
    # this is made automatically in the database
    # it's not available durning insertion, but during retreval it's available
    # so we make it optional, and its type is object
    id: Optional[ObjectId]=Field(default=None, alias="_id")
    # put conditions for the id
    project_id: str = Field(..., min_length=1)

    # pydantic can't understand type of: ObjectId, so we add this part of code to be able to deal with it
    class Config:
        arbitrary_types_allowed=True