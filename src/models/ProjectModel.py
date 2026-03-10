from .BaseData import BaseData
from .schemas import Project
from .enums.DatabaseEnum import DatabaseEnum
import logging
from sqlalchemy.future import select
from sqlalchemy import func




class ProjectModel(BaseData):
    def __init__(self, client: object):
        super().__init__(client)
        self.client= client
    

    # init_collection is a async method, so we should call it with await, 
    # we can't call async method in __init__ 
    # so we make this method to call __init__ and init_collection
    @classmethod
    async def create_instance(cls, client: object):
        instance= cls(client)
        return instance

    log=logging.getLogger('uvicorn.error')
    
    async def create_project(self, project: Project):
        async with self.client() as session:
            async with session.begin():
                session.add(project)
            await session.commit()
            await session.refresh(project)
        return project



    # if the project with given id not found, create one
    async def get_or_create_project(self, project_id: str):
        async with self.client() as session:
            async with session.begin():
                query=select(Project).where(Project.project_id==project_id)
                project=await session.execute(query)
                project=project.scalar_one_or_none()
                if project is None:
                    project_rec= Project(
                        project_id=project_id
                    )
                    await self.create_project(project_rec)
                    return project
                else:
                    return project

    

    async def get_all_projects(self, page: int=1, page_size: int=10):
        
        async with self.client() as session:
            async with session.begin():    
                total_docs=await session.execute(select(
                    func.count(Project.project_id)
                )).scalar_one()
                total_pages=total_docs // page_size
                if total_docs % page_size >0 :
                    total_pages+=1
                query= select(Project).offset((page -1) * page_size).limit(page_size)
                projects=await session.execute(query).scalars().all()
                return projects, total_pages
    
    