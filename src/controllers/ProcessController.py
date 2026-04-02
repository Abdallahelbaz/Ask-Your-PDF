from .BaseController import BaseController
from .ProjectController import ProjectController
import os
from langchain_community.document_loaders import PyMuPDFLoader, JSONLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter,CharacterTextSplitter
from models import ProcessingEnums
import re
from langchain_core.documents import Document
import json
from typing import List, Tuple
from models.schemas import Chunk

class ProcessController(BaseController):

    def __init__(self, project_id:str):
        super().__init__()
        self.project_id=project_id
        self.project_path= ProjectController().get_project_path(project_id=project_id)
        
    

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
        elif file_extenstion == ProcessingEnums.JSON.value:
            return JSONLoader(file_path=file_path,jq_schema=".[]", text_content=False)
        
        return None
    
    def get_file_content(self, file_id:str):
        loader= self.get_file_loader(file_id=file_id)
        if loader:
            return loader.load()
        return None
    




    
    


    def process_file_content_2(self, file_content: list, file_id: str,
                            chunk_size: int=900, overlap_size: int=100):
        file_content = self.remove_bgb_header(file_content)
        text_splitter= RecursiveCharacterTextSplitter(
            chunk_size= chunk_size,
            chunk_overlap= overlap_size,
            length_function= len,
            keep_separator=True,
            # separators=[
            # "\n§ ",  # New section
            # "\n\n",  # Paragraph breaks
            # "\n",    # Line breaks
            # ". ",    # Sentences
            # " ",     # Words
            # ]
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
    
    

    def split_absatz(self,text: str):

        pattern = r'(\(\d+\))'

        parts = re.split(pattern, text)

        absatze = []

        for i in range(1, len(parts), 2):
            number = parts[i]
            content = parts[i+1]
            absatze.append(number + content)

        return absatze


    # def process_file_content(self, file_content: list, asset_id: int, project_id: int, chunk_size: int, overlap_size: int):
    #     parent_chunks = []
    #     child_data_list = []

    #     child_splitter = RecursiveCharacterTextSplitter(
    #         chunk_size=chunk_size, 
    #         chunk_overlap=overlap_size
    #     )

    #     for rec in file_content:
    #         try:
    #             data = json.loads(rec.page_content)
    #         except: continue

    #         # Create Parent Object
    #         parent_text = f"{data.get('full_section', '')}\n{data.get('text', '')}"
    #         parent_obj = Chunk(
    #             chunk_text=parent_text,
    #             chunk_project_id=project_id,
    #             chunk_asset_id=asset_id,
    #             chunk_metadata={"law": data.get("law"), "section": data.get("section")},
    #             chunk_order=0
    #         )
    #         parent_chunks.append(parent_obj)
    #         text = data.get("text", "")

    #         # Prepare Child Data (Wait for parent_id)
    #         child_source = f"Keywords: {', '.join(data.get('keywords', []))}\n{data.get('text', '')}"

    #         absatze = self.split_absatz(text)
    #         full_section=data.get('full_section', '')
    #         keywords=data.get('keywords', [])

    #         if not absatze:
    #             absatze = [text]

    #         child_subtexts = []

    #         for absatz in absatze:

    #             absatz_content = f"{full_section}\n{absatz}"
    #             # absatz_content = f"{full_section}\n{absatz}\nKeywords: {', '.join(keywords)}"
    #             # # if absatz small → keep
    #             # if len(absatz_content) <= chunk_size:

    #             child_subtexts.append(absatz_content)

    #             # else:
    #             #     splits = recursive_splitter.split_text(absatz_content)
    #             #     child_subtexts.extend(splits)
            
    #         child_data_list.append({
    #             "sub_texts": child_subtexts,
    #             "metadata": {
    #                 "law": data.get("law"), 
    #                 "section": data.get("section"), 
    #                 "keywords": data.get("keywords", [])
    #             }
    #         })

    #     return parent_chunks, child_data_list



    def process_file_content(self, file_content: list, file_id: str,
                         chunk_size: int=900, overlap_size: int=100):
        docs = []
        for rec in file_content:
            try:
                data = json.loads(rec.page_content)  # parse the JSON string
            except json.JSONDecodeError:
            # skip invalid JSON lines
                 continue
            # If page_content is a dict (JSON)
            
            paragraph = data.get("paragraph", "").strip()
            print(paragraph)
            titel=data.get("titel","").strip()
            text = data.get("text", "").strip()
            questions = data.get("questions", "").strip()

            content = f"{paragraph}\n{titel}\n{text}\n{questions}" if text else None
            # If page_content is a string (TXT or PDF)
            if not content:
                continue

            docs.append(
                Document(
                    page_content=content,
                    metadata={
                        "paragraph": paragraph,
                        "file_id": file_id,
                        "key_words":titel
                    }
                )
            )

        return docs


    def process_file_content_ID_1(self, file_content: list, file_id: str,
                         chunk_size: int=900, overlap_size: int=100):
        docs = []
        for rec in file_content:
            try:
                data = json.loads(rec.page_content)  # parse the JSON string
            except json.JSONDecodeError:
            # skip invalid JSON lines
                 continue
            # If page_content is a dict (JSON)
            
            paragraph = data.get("full_section", "").strip()
            print(paragraph)

            text = data.get("text", "").strip()
            print(text)
            keywords = data.get("keywords", [])
            print(keywords)
            content = f"{paragraph}\n{text}\n{keywords}" if text else None
            # If page_content is a string (TXT or PDF)
            if not content:
                continue

            docs.append(
                Document(
                    page_content=content,
                    metadata={
                        "paragraph": paragraph,
                        "file_id": file_id,
                        "key_words":keywords
                    }
                )
            )

        return docs

    def process_file_content_ID_2(self, file_content: list, file_id: str,
                         chunk_size: int=900, overlap_size: int=100):
        docs = []
        for rec in file_content:
            try:
                data = json.loads(rec.page_content)  # parse the JSON string
            except json.JSONDecodeError:
            # skip invalid JSON lines
                 continue
            # If page_content is a dict (JSON)
            paragraph = data.get("paragraph", "").strip()
            print(paragraph)
            text = data.get("text", "").strip()
            print(text)
            content = f"{paragraph}\n{text}" if text else None
            # If page_content is a string (TXT or PDF)
            if not content:
                continue
            docs.append(
                Document(
                    page_content=content,
                    metadata=rec.metadata
                )
            )

        return docs
    
    def process_file_content_ID_3(self, file_content: list, file_id: str,
                            chunk_size: int=1000, overlap_size: int=100):
        file_content = self.remove_bgb_header(file_content)
        text_splitter= RecursiveCharacterTextSplitter(
            chunk_size= chunk_size,
            chunk_overlap= overlap_size,
            length_function= len,
        )
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


    def process_file_content_ID_4(self, file_content: list, file_id: str,
                             chunk_size: int = 500, overlap_size: int = 50):

        file_content = self.remove_bgb_header(file_content)
        full_text = " ".join([rec.page_content for rec in file_content])
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap_size,
            length_function=len,
        )

        docs = []

        for rec in file_content:

            text = rec.page_content
            metadata = rec.metadata

            # Split by paragraph (§)
            sections = re.split(r'(§\s*\d+\s+[^\n]+)', text)

            for i in range(1, len(sections), 2):
                paragraph_title = sections[i].strip()
                paragraph_text = sections[i+1].strip()

                full_text = f"{paragraph_title}\n{paragraph_text}"

                # Now apply recursive splitter
                sub_chunks = text_splitter.split_text(full_text)

                for chunk in sub_chunks:
                    docs.append(
                        Document(
                            page_content=chunk,
                            metadata={
                                **metadata,
                                "paragraph": paragraph_title,
                                "file_id": file_id
                            }
                        )
                    )

        return docs
    
    def process_file_content_ID_5(self, file_content: list, file_id: str,
                            chunk_size: int=1000, overlap_size: int=100):
        file_content = self.remove_bgb_header(file_content)
        text_splitter= CharacterTextSplitter(
            separator="§",
            chunk_size=chunk_size,
            chunk_overlap=overlap_size,
            length_function=len,
            is_separator_regex=False,
        )
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






    def remove_bgb_header(self, file_content: list) -> list:
        """
        Aggressively remove the specific Bundesministerium header and 
        '- Seite X von Y -' footers from the BGB document.
        """
        print("Hello from: remove_bgb_header (Updated for 2026 Layout)")
        
        cleaned_content = []
        
        # 1. Regex for the specific footer: - Seite 27 von 488 -
        # Matches: hyphen, optional space, "Seite", numbers, "von", numbers, optional space, hyphen
        footer_pattern = r'-\s*Seite\s+\d+\s+von\s+\d+\s*-'
        
        # 2. Updated Header patterns based on your specific text
        # We use \s+ to handle line breaks between "Justiz" and "und für Verbraucherschutz"
        header_patterns = [
            r'Ein Service des Bundesministeriums? der Justiz und für Verbraucherschutz',
            r'sowie des Bundesamts für Justiz',
            r'www\.gesetze-im-internet\.de',
            r'‒' # The specific dash character used in the footer/header
        ]

        for doc in file_content:
            if hasattr(doc, 'page_content'):
                text = doc.page_content
                
                # --- Step A: Remove Footer (- Seite X von Y -) ---
                text = re.sub(footer_pattern, '', text, flags=re.IGNORECASE)
                
                # --- Step B: Remove specific header blocks ---
                # Using multi-line regex to catch the whole block if it appears together
                full_header_pattern = (
                    r'Ein Service des Bundesministeriums? der Justiz und für Verbraucherschutz\s+'
                    r'sowie des Bundesamts für Justiz\s*[‒-]\s*www\.gesetze-im-internet\.de'
                )
                text = re.sub(full_header_pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
                
                # --- Step C: Individual Part Removal ---
                for pattern in header_patterns:
                    text = re.sub(pattern, '', text, flags=re.IGNORECASE)
                
                # --- Step D: Line-by-line validation ---
                lines = text.split('\n')
                cleaned_lines = []
                
                for line in lines:
                    line_stripped = line.strip()
                    # Skip the specific footer/header fragments if they survived
                    if any(phrase in line_stripped for phrase in [
                        'Bundesministerium der Justiz',
                        'Bundesamts für Justiz',
                        'gesetze-im-internet.de',
                        'Verbraucherschutz'
                    ]):
                        continue
                    
                    # Check for the lone page count line that sometimes splits
                    if re.match(r'^Seite \d+ von \d+$', line_stripped):
                        continue
                        
                    cleaned_lines.append(line)
                
                text = '\n'.join(cleaned_lines)
                
                # --- Step E: Clean up excessive newlines ---
                text = re.sub(r'\n{3,}', '\n\n', text)
                
                doc.page_content = text.strip()
                cleaned_content.append(doc)
        
        return cleaned_content
