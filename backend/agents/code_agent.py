import re
from typing import Dict, Any

from core.pipeline import PipelineStep, step_logging_wrapper
from config import settings
from services.llm_service import LLMService

class CodeAgent(PipelineStep):
    """
    LLM Engineer Agent responsible for generating Python Pandas code.
    It takes the highly structured prompt from the PromptAgent and uses the centralized LLMService
    to generate the precise analytical code required.
    """
    
    def __init__(self):
        # Delegate LLM interactions to the standardized service
        self.llm_service = LLMService(
            api_key=settings.GROQ_API_KEY,
            default_model=settings.GROQ_MODEL
        )
        
    @step_logging_wrapper
    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sends the structured prompt to Groq and extracts the generated Python code.
        """
        structured_prompt = state.get("structured_prompt")
        
        if not structured_prompt:
            raise ValueError("CodeAgent requires 'structured_prompt' in the state context.")
            
        try:
            # Call centralized LLM logic
            raw_response = await self.llm_service.generate_response(
                prompt=structured_prompt,
                temperature=0.1,  # Low temperature for highly deterministic, focused code output
                max_tokens=4096
            )
            
            # Extract clean Python code (often wrapped in ```python ... ``` by LLMs)
            generated_code = self._extract_code(raw_response)
            
            return {
                "generated_code": generated_code,
                "raw_llm_response": raw_response
            }
            
        except Exception as e:
            raise RuntimeError(f"CodeAgent failed during LLM generation: {str(e)}")
            
    def _extract_code(self, raw_text: str) -> str:
        """
        Extracts clean, executable Python code from the LLM's markdown-formatted string.
        """
        if not raw_text:
            return ""
            
        # 1. Look for explicit code blocks: ```python ... ``` or just ``` ... ```
        pattern = r"```(?:python)?\s*(.*?)\s*```"
        match = re.search(pattern, raw_text, re.DOTALL | re.IGNORECASE)
        
        if match:
            return match.group(1).strip()
            
        # 2. Fallback: Identify if the LLM output naked code
        # We assume the LLM followed instructions and output only Python code.
        clean_text = raw_text.strip()
        # Further strip incomplete or malformed markdown markers just in case
        clean_text = re.sub(r"^```\w*\s*", "", clean_text)
        clean_text = re.sub(r"\s*```$", "", clean_text)
        
        return clean_text.strip()
