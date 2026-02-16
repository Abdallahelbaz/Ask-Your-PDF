from .BaseController import BaseController
from .ProjectController import ProjectController
from fastapi import UploadFile
from models import ResponseEnum
import os
import re

class DataController(BaseController):
    def __init__(self):
        super().__init__()

    def validate_file(self, file: UploadFile):
        if not file.content_type in self.settings.FILE_ALLOWED_TYPES:
            return False, ResponseEnum.FILE_TYPE_NOT_SUPPORTED.value
        
        if file.size > self.settings.FILE_MAX_SIZE_MB * 1024 * 1024:
            return False,ResponseEnum.FILE_SIZE_EXCEEDED.value
    
        return True, ResponseEnum.FILE_UPLOADED_SUCCESSFULLY.value
    
    def generate_unique_filepath(self, original_file_name:str, project_id:str ):
        random_filename= self.generate_random_string()
        project_path = ProjectController().get_project_path(project_id=project_id)
        cleaned_filename= self.get_clean_file_name(original_file_name)
        new_file_path= os.path.join(
            project_path,
            random_filename + "_" + cleaned_filename
        )

        while os.path.exists(new_file_path):
            random_filename= self.generate_random_string()
            new_file_path= os.path.join(
            project_path,
            random_filename + "_" + cleaned_filename
        )
        return new_file_path, random_filename + "_" + cleaned_filename

    def get_clean_file_name(self, orig_file_name: str):

        # remove any special characters, except underscore and .
        cleaned_file_name = re.sub(r'[^\w.]', '', orig_file_name.strip())

        # replace spaces with underscore
        cleaned_file_name = cleaned_file_name.replace(" ", "_")

        return cleaned_file_name
