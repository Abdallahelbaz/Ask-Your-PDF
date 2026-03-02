from enum import Enum

class ResponseEnum(Enum):

    FILE_TYPE_NOT_SUPPORTED="File Type Not Supported"
    FILE_SIZE_EXCEEDED= "File Size Exceeded"
    FILE_UPLOADED_SUCCESSFULLY="File Uploaded Successfully"
    FILE_UPLOADED_FAILED= "File Uploaded Failed"
    FILE_VALIDATED_SUCCESS= "File Validated Success"
    FILE_VALIDATED_FAILED="File Validation Failed"
    PROCESSING_FAILED="Failed Processing"
    PROCESSING_SUCCESS="Processing Success"
    NO_FILES_SIGNAL="There are no files!"
    PROJECT_NOT_FOUND="Project Not Found!"
    INSERT_INTO_VECTORDB_ERROR="Insert Into VectorDB Error"
    INSERT_INTO_VECTORDB_SUCCESS="Insertion Successfull"
    VECTORDB_COLLECTION_INFO="VectorDB Collection info retrieved"
    VECTORDB_SEARCH_INFO="Hier is the search info"
