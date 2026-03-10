from .BaseData import BaseData
from .schemas import Asset
from .enums.DatabaseEnum import DatabaseEnum
import logging
from sqlalchemy.future import select
from sqlalchemy import func, delete
from bson import ObjectId


class AssetModel(BaseData):
    def __init__(self, client: object):
        super().__init__(client)
        self.client= client

    @classmethod
    async def create_instance(cls, client: object):
        instance = cls(client)
        return instance
    


    async def create_asset(self, asset: Asset):
        async with self.client() as session:
            async with session.begin():
                session.add(asset)
            await session.commit()
            await session.refresh(asset)
        return asset
    

    async def get_all_project_assets(self, asset_project_id: str, asset_type: str):
        
        async with self.client() as session:
            query= select(Asset).where(
                    Asset.asset_project_id==asset_project_id,
                    Asset.asset_type==asset_type
                )
                
            assets=await session.execute(query)
            assets=assets.scalars().all()
        return assets
    
    async def get_asset_record(self, asset_project_id: str, asset_name: str):
        async with self.client() as session:
            query= select(Asset).where(
                    Asset.asset_project_id==asset_project_id,
                    Asset.asset_name==asset_name
                )
                
            asset=await session.execute(query)
            asset=asset.scalar_one_or_none()
        return asset
    