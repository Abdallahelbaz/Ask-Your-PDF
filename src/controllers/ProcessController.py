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
    
    



    def process_file_content_json(self, file_content: list, asset_id: int, project_id: int, chunk_size: int, overlap_size: int, file_id: str):
        print('\n Hello From Process Json \n')
        parent_chunks = []
        child_chunks_nested = []
        
        child_splitter = RecursiveCharacterTextSplitter(
            chunk_size=300, 
            chunk_overlap=50
        )

        for rec in file_content:
            try:
                data = json.loads(rec.page_content)
            except: 
                continue

            full_section = data.get('full_section', '')
            text = data.get("text", "")
            
            # Create Parent Object
            parent_text = f"{full_section}\n{text}"
            parent_obj = Chunk(
                chunk_text=parent_text,
                chunk_project_id=project_id,
                chunk_asset_id=asset_id,
                chunk_metadata={"paragraph": full_section},
                chunk_order=0
            )
            parent_chunks.append(parent_obj)

            # 2. Handle Splitting Logic
            if len(text) > 300:
                # Recursive split (tries to stay under 500)
                raw_docs = child_splitter.split_text(text)
                
                # 3. Merge Logic to enforce MINIMUM 250
                refined_docs = []
                for chunk in raw_docs:
                    if refined_docs and len(chunk) < 200:
                        # Append small chunk to the previous one
                        refined_docs[-1] = f"{refined_docs[-1]} {chunk}".strip()
                    else:
                        refined_docs.append(chunk)
                
                # Final check: if the very last chunk is still < 250 and we have more than one chunk
                if len(refined_docs) > 1 and len(refined_docs[-1]) < 200:
                    last_chunk = refined_docs.pop()
                    refined_docs[-1] = f"{refined_docs[-1]} {last_chunk}".strip()
            else:
                refined_docs = [text]

            # 4. Create Child Objects
            current_parent_children = []
            for i, absatz in enumerate(refined_docs):
                absatz_content = f"{full_section}\n{absatz}"
                child_obj = Chunk(
                    chunk_text=absatz_content,
                    chunk_project_id=project_id,
                    chunk_asset_id=asset_id,
                    chunk_metadata={"paragraph": full_section},
                    chunk_order=i  # Using i to maintain sequence
                )
                current_parent_children.append(child_obj)
            
            child_chunks_nested.append(current_parent_children)

        return child_chunks_nested, parent_chunks



    def process_file_content_pdf(self, file_content: list, file_id: str,
                         chunk_size: int=1000, overlap_size: int=5, 
                         project_id=None, asset_id=str):
        print('\n Hello From Process pdf \n')
        # 1. Pre-process (Header removal and Regex cleaning)
        file_content = self.remove_bgb_header(file_content)
        cleaned_string = self.clean_text(file_content) 

        # 2. Wrap into Document object
        cleaned_docs = [Document(page_content=cleaned_string, metadata={"file_id": file_id})]

        # Define Splitters
        parent_splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=0)
        child_splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=50)

        # Create Parent Documents
        parent_docs = parent_splitter.create_documents(
            [rec.page_content for rec in cleaned_docs],
            metadatas=[rec.metadata for rec in cleaned_docs]
        )

        final_parents = []
        final_children = []

        # 2. For each parent, generate its specific children
        for p_idx, p_doc in enumerate(parent_docs):
            parent_obj = Chunk(
                chunk_text=p_doc.page_content,
                chunk_metadata={"type": "parent", "file_id": file_id, "metadata": p_doc.metadata},
                chunk_order=p_idx,
                chunk_project_id=project_id,
                chunk_asset_id=asset_id
            )
            final_parents.append(parent_obj)

            # 3. Split Parent into children
            child_docs = child_splitter.create_documents([p_doc.page_content])
            
            parent_children_data = []
            for c_idx, c_doc in enumerate(child_docs):

                # Only keep the child if it's 300 characters or more
                if len(c_doc.page_content) >= 200:
                    child_data = Chunk(
                        chunk_text=c_doc.page_content,
                        chunk_metadata={"type": "child", "file_id": file_id, "metadata": p_doc.metadata},
                        chunk_order=c_idx,
                        chunk_project_id=project_id,
                        chunk_asset_id=asset_id
                    )
                    parent_children_data.append(child_data)
                else:
                    pass
            
            # Only add to final_children if the parent actually produced valid children
            final_children.append(parent_children_data)

        return final_children, final_parents



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


    def clean_text(self, raw_text):
        # 1. Check if it's a list of LangChain Document objects
        if isinstance(raw_text, list):
            try:
                # Extract 'page_content' from each Document object
                raw_text = "\n".join([doc.page_content for doc in raw_text])
            except AttributeError:
                # Fallback if it's just a list of strings
                raw_text = "\n".join([str(item) for item in raw_text])
        
        # 2. Perform the cleaning regex
        text = re.sub(r'\n\s*\n', '\n', raw_text)
        text = re.sub(r'[ \t]+', ' ', text)
        
        return text.strip()