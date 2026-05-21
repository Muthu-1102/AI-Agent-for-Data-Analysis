from typing import Optional

from groq import AsyncGroq
from utils.logger import log_llm_interaction

class LLMService:
    """
    Service responsible for interacting with the Groq API.
    Provides a standardized abstraction so agents don't need to manually
    manage HTTP clients, endpoints, or API keys natively.
    """
    def __init__(self, api_key: str, default_model: str = "llama-3.1-8b-instant"):
        self.api_key = api_key
        self.default_model = default_model
        # Initialize the global Groq client instance for this service
        self.client = AsyncGroq(api_key=self.api_key)
        
    async def generate_response(self, prompt: str, model: Optional[str] = None, temperature: float = 0.1, max_tokens: int = 4096) -> str:
        model = model or self.default_model
        """
        Submits a prompt to Groq and extracts the raw textual response.
        Allows customization of model constraints.
        """
        try:
            response = await self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            raw_content = response.choices[0].message.content
            
            # Log the exact prompt and response specifically for debugging/tracing
            log_llm_interaction(prompt=prompt, response=raw_content, model=model)
            
            return raw_content
        except Exception as e:
            raise RuntimeError(f"LLM generation failed: {str(e)}")
