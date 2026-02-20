from .BaseData import BaseData
from .schemas import Project
from .enums.DatabaseEnum import DatabaseEnum
import logging

class ProjectModel(BaseData):
    def __init__(self, client: object):
        super().__init__(client)
        self.collection= self.client[DatabaseEnum.COLLECTION_PROJECT.value]
    

    # init_collection is a async method, so we should call it with await, 
    # we can't call async method in __init__ 
    # so we make this method to call __init__ and init_collection
    @classmethod
    async def create_instance(cls, client: object):
        instance= cls(client)
        await instance.init_collection()
        return instance

    # create Index
    async def init_collection(self):
        # see first if the collection available or not, if not, create indexes
        all_coll= await self.client.list_collection_names()
        if DatabaseEnum.COLLECTION_PROJECT.value not in all_coll:
            self.collection= self.client[DatabaseEnum.COLLECTION_PROJECT.value]
            indexes= Project.get_indexes()
            for index in indexes:
                await self.collection.create_index(
                    index["key"],
                    name=index["name"],
                    unique=index["unique"]
                )

    log=logging.getLogger('uvicorn.error')
    
    # should be async, because insertion (motor) is async, we should call it with await
    async def create_project(self, project: Project):
        # model_dump() to convert data to dict
        # to get the data by its alias, exclude none values
        insert_value= await self.collection.insert_one(project.model_dump(by_alias=True, exclude_unset=True))
        project.id=insert_value.inserted_id
        self.log.error(f"Error While Uploading: {project.id}")
        return project.id
    
    # if the project with given id not found, create one
    async def get_or_create_project(self, project_id: str):
        # it returns dic
        value= await self.collection.find_one({
            "project_id": project_id
        })
        self.log.error(f"I'm in get_or_create_project {value}")
        if value is None:
            project= Project(project_id=project_id)
            project=await self.create_project(project)
            return project
        
        # to convert each value in dict, to project, we use **
        return Project(**value)
    
    # if we loaded all data in one page, by big projects, it will be overload on the newtwork
    # so, loaded for example 10 by 10
    async def get_all_projects(self, page: int=1, page_size: int=10):
        
        # count number of docs, there is no conditions, so {} is empty
        total_docs= self.collection.count_documents({})

        # calculate total pages
        total_pages= total_docs // page_size
        # if total pages is 20.1, so we want to make a new page for this 0.1
        if total_docs % page_size>0:
            total_pages+=1
        
        # if i'm in the second page, so it will skip first 10 and start from record 11
        cursor=self.collection.find().skip((page-1) * page_size).limit(10)
        # now we want to load it one by one to be more memory efficint
        projects=[]
        async for doc in cursor:
            projects.append(
                Project(**doc)
            )   

        return projects, total_pages     


    
    