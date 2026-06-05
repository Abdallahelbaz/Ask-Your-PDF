from .providers.QdrantDB import QdrantDB
from .providers.PgVector import PgVector
from .VectorDBbEnums import VectorDBbEnums, DistanceMethodEnum
from controllers.BaseController import BaseController
from sqlalchemy.orm import sessionmaker

class VectorDBFactory:
    def __init__(self,config, db_client: sessionmaker= None):
        self.config=config
        self.base_controller= BaseController()
        self.db_client=db_client

    def create(self, provider:str):
        if provider== VectorDBbEnums.QDRANT.value:
            dp_path=self.base_controller.get_database_path(db_name=self.config.VECTOR_DB_PATH)
            return QdrantDB(
                db_path=dp_path,
                distance_method=self.config.VECTOR_DB_DISTANCE_METHPD
            )
        if provider== VectorDBbEnums.PGVECTOR.value:
            dp_path=self.base_controller.get_database_path(db_name=self.config.VECTOR_DB_PATH)
            return PgVector(
                db_client=self.db_client,
                distance_method=self.config.VECTOR_DB_DISTANCE_METHPD,
                index_threshold=self.config.VECTOR_DB_PGVECTOR_INDEX_THRESHOLD
            )
        return None