"""
app/llm/llama3_provider.py
Llama3 LLM provider implementation
"""
import httpx
import logging
from typing import List, Optional, Dict, Any

from .base import BaseLLMProvider, LLMResponse, LLMMessage, LLMProvider


logger = logging.getLogger(__name__)


class Llama3Provider(BaseLLMProvider):
    """Llama3 LLM provider"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.provider_name = LLMProvider.LLAMA3
        self.api_url = config.get("llama3_api_url", "https://fastchat.ideeza.com/v1/chat/completions")
        self.model = config.get("llama3_model", "llama-3")
        self.timeout = config.get("timeout", 60.0)
        self.api_key = config.get("llama3_api_key")  # If needed
        
    async def generate(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate response using Llama3 API"""
        
        formatted_messages = self.format_messages(messages)
        
        payload = {
            "model": self.model,
            "messages": formatted_messages,
            "temperature": temperature,
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
            
        # Add any additional kwargs
        payload.update(kwargs)
        
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.api_url,
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                
                data = response.json()
                
                # Parse response following OpenAI format
                content = data["choices"][0]["message"]["content"]
                finish_reason = data["choices"][0].get("finish_reason")
                tokens_used = data.get("usage", {}).get("total_tokens")
                
                return LLMResponse(
                    content=content,
                    provider=self.provider_name,
                    tokens_used=tokens_used,
                    finish_reason=finish_reason,
                    model=self.model,
                    metadata={
                        "usage": data.get("usage"),
                        "id": data.get("id")
                    }
                )
                
        except httpx.TimeoutException as e:
            logger.error(f"Llama3 API timeout: {e}")
            raise Exception(f"Llama3 timeout: {e}")
        except httpx.HTTPStatusError as e:
            logger.error(f"Llama3 API HTTP error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Llama3 HTTP error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Llama3 API error: {e}")
            raise Exception(f"Llama3 error: {e}")
    
    async def health_check(self) -> bool:
        """Check if Llama3 API is available"""
        try:
            # Simple health check with minimal payload
            test_messages = [LLMMessage(role="user", content="test")]
            await self.generate(test_messages, max_tokens=5)
            return True
        except Exception as e:
            logger.warning(f"Llama3 health check failed: {e}")
            return False
    
    def get_provider_type(self) -> LLMProvider:
        """Return provider type"""
        return self.provider_name