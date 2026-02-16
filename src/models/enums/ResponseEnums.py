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
