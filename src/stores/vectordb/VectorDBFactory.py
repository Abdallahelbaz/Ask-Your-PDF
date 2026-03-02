from .providers.QdrantDB import QdrantDB
from .VectorDBbEnums import VectorDBbEnums, DistanceMethodEnum
from controllers.BaseController import BaseController

class VectorDBFactory:
    def __init__(self,config):
        self.config=config
        self.base_controller= BaseController()

    def create(self, provider:str):
        if provider== VectorDBbEnums.QDRANT.value:
            dp_path=self.base_controller.get_database_path(db_name=self.config.VECTOR_DB_PATH)
            return QdrantDB(
                db_path=dp_path,
                distance_method=self.config.VECTOR_DB_DISTANCE_METHPD
            )
        return None