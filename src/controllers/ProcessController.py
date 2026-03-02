from .BaseController import BaseController
from .ProjectController import ProjectController
import os
from langchain_community.document_loaders import TextLoader
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter,CharacterTextSplitter
from models import ProcessingEnums
import re
from langchain_core.documents import Document


class ProcessController(BaseController):

    def __init__(self, project_id:str):
        super().__init__()
        self.project_id=project_id
        self.project_path= ProjectController().get_project_path(project_id=project_id)
        self.SECTION_START_RE = re.compile(r"(?m)^\s*§\s*(\d+[a-z]?)\b")
    

    def get_file_extenstion(self, file_id:str):
        return os.path.splitext(file_id)[-1]

    def get_file_loader(self, file_id:str):
        file_extenstion= self.get_file_extenstion(file_id)
        file_path=os.path.join(
            self.project_path,
            file_id
        )
        if not os.path.exists(file_path):
            return None
    
        if file_extenstion == ProcessingEnums.TXT.value:
            return TextLoader(file_path, encoding="utf-8")
        elif file_extenstion == ProcessingEnums.PDF.value:
            return PyMuPDFLoader(file_path)
        
        return None
    
    def get_file_content(self, file_id:str):
        loader= self.get_file_loader(file_id=file_id)
        if loader:
            return loader.load()
        return None
    

    def process_file_content(self, file_content: list, file_id: str,
                            chunk_size: int=500, overlap_size: int=20):
        
        text_splitter= RecursiveCharacterTextSplitter(
            chunk_size= chunk_size,
            chunk_overlap= overlap_size,
            length_function= len,
            separators=[
            "\n§ ",  # New section
            "\n\n",  # Paragraph breaks
            "\n",    # Line breaks
            ". ",    # Sentences
            " ",     # Words
            ]
        )
        
        # text_splitter= CharacterTextSplitter(
        #     separator="§",
        #     chunk_size=chunk_size,
        #     chunk_overlap=overlap_size,
        #     length_function=len,
        #     is_separator_regex=False,
        # )
        file_content_text=[
            rec.page_content
            for rec in file_content
        ]
        file_content_metadata=[
            #{'page':rec.metadata.get('page')}
            rec.metadata
            for rec in file_content
        ]

        chunks= text_splitter.create_documents(
            file_content_text,
            metadatas=file_content_metadata,
           
        )
        return chunks



    # def process_file_content(self, file_content: list, file_id: str, 
    #                         chunk_size: int=800, overlap_size: int=100):
        
    #     # 1. Define the splitter
    #     text_splitter = RecursiveCharacterTextSplitter(
    #         chunk_size=chunk_size,
    #         chunk_overlap=overlap_size,
    #         length_function=len,
    #         separators=[
    #             "\n§ ",  # Priority: Start of a new legal section
    #             "\n\n",  # Paragraph breaks
    #             "\n",    # Line breaks
    #             ". ",    # Sentences
    #             " ",     # Words
    #         ]
    #     )

    #     enriched_docs = []

    #     for doc in file_content:
    #         # 2. Extract the Section Number
    #         # We try to find something like "§ 400" or "§400" in the text
    #         content = doc.page_content
    #         section_match = re.search(r"§\s*\d+[a-z]?", content)
            
    #         # Fallback to metadata if regex doesn't find it
    #         section_id = section_match.group(0) if section_match else doc.metadata.get("section", "Allgemein")

    #         # 3. Contextual Injection
    #         # Prepend the section info so it exists in EVERY chunk after splitting
    #         doc.page_content = f"BGB {section_id}: {content}"
    #         enriched_docs.append(doc)

    #     # 4. Split the enriched documents into final chunks
    #     chunks = text_splitter.split_documents(enriched_docs)

        
    #     return chunks

    

