from ..llm.LLMInterface import LLMInterface
from openai import OpenAI
import logging
from ..llm.LLMEnum import BGEEnum
from ..llm.LLMEnum import DocumentTypeEnum

class BGEProvider(LLMInterface):

    def __init__(self, api_key: str, api_url: str= None, 
                    default_input_max_chars: int = 1000,
                    default_max_output_tokens: int= 1000,
                    temperature: float= 0.1):
        self.api_key=api_key
        self.api_url=api_url
        self.default_input_max_chars=default_input_max_chars
        self.default_max_output_tokens=default_max_output_tokens
        self.temperature=temperature
        self.generation_model_id= None
        self.embedding_model_id= None
        self.embedding_size= None
        
        
        self.client= OpenAI(
            api_key=self.api_key,
            base_url=self.api_url,
        )
        self.log= logging.getLogger(__name__)



    def set_generation_model(self, model_id:str):
        self.generation_model_id= model_id


    def set_embedding_model(self, model_id:str, model_size: int):
        self.embedding_model_id= model_id
        self.embedding_size= model_size


    def generate_text(self, prompt: str,chat_history: list, max_output_tokens: int= None, temperature: float= None):
        pass


    def process_text(self, text:str):
        return text[:self.default_input_max_chars].strip()


    def ebmed_text(self, text: str, document_type: str= None):
        if not self.client:
            self.log.error("Embedding Not set")
            return None
        
        if not self.embedding_model_id: 
            self.log.error("Embedding Model Id not set")
            return None

        response= self.client.embeddings.create(
            model= self.embedding_model_id,
            input=  text
        )

        if not response or not response.data or len(response.data)==0 or not response.data[0].embedding:
            self.log.error("Error While Embedding Text")
            return None
        return response.data[0].embedding

    def construct_prompt(self, prompt: str, role: str):
        return {
            "role": role,
            "content": self.process_text(prompt)
        }