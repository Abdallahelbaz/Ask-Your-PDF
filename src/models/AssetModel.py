from .BaseData import BaseData
from .schemas import Asset
from .enums.DatabaseEnum import DatabaseEnum
import logging
from bson import ObjectId

class AssetModel(BaseData):
    def __init__(self, client: object):
        super().__init__(client)
        self.collection= self.client[DatabaseEnum.COLLECTION_ASSETS.value]

    @classmethod
    async def create_instance(cls, client: object):
        instance = cls(client)
        await instance.init_collection()
        return instance
    
    async def init_collection(self):
        # see first if the collection available or not, if not, create indexes
        all_coll= await self.client.list_collection_names()
        if DatabaseEnum.COLLECTION_ASSETS.value not in all_coll:
            self.collection= self.client[DatabaseEnum.COLLECTION_ASSETS.value]
            indexes= Asset.get_indexes()
            for index in indexes:
                await self.collection.create_index(
                    index["key"],
                    name=index["name"],
                    unique=index["unique"]
                )
    

    async def create_asset(self, asset: Asset):
        result= await self.collection.insert_one(asset.model_dump(by_alias=True, exclude_unset=True))
        asset.id = result.inserted_id
        return asset
    

    async def get_all_project_assets(self, asset_project_id):
        return await self.collection.finid({
            "asset_project_id": ObjectId(asset_project_id) if isinstance(asset_project_id, str) else asset_project_id
            # if i need all, i write None, length=10
        }).to_list(length=None)