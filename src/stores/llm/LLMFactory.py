from .LLMEnum import LLMEnum
from ..providers.QwenProvider import QwenProvider
from ..providers.BGEProvider import BGEProvider

class LLMFactory:

    def __init__(self, config:dict):
        self.config=config
    
    def create(self, provider: str):

        if provider == LLMEnum.QWEN.value:
            return QwenProvider(
                api_key= self.config.QWEN_API_KEY,
                 api_url= self.config.QWEN_URL, 
                    default_input_max_chars=self.config.INPUT_DEFAULT_MAX_CHARS,
                    default_max_output_tokens=self.config.GENERATION_DEFAULT_MAX_TOKENS,
                    temperature= self.config.GENERATION_DEFAULT_TEMPERATURE
            )
        if provider == LLMEnum.BGE.value:
            return BGEProvider(
                api_key= self.config.BGE_API_KEY,
                 api_url= self.config.BGE_URL, 
                    default_input_max_chars=self.config.INPUT_DEFAULT_MAX_CHARS,
                    default_max_output_tokens=self.config.GENERATION_DEFAULT_MAX_TOKENS,
                    temperature= self.config.GENERATION_DEFAULT_TEMPERATURE
            )
        
        return None

