from abc import ABC, abstractmethod
from typing import Dict, Any
import json
import httpx
from app.config import settings
from app.schemas import SummarySectionOutput


class LLMClient(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    async def generate_summary(self, section_text: str, section_key: str = None, heading: str = None) -> SummarySectionOutput:
        """Generate a grounded summary for a bill section"""
        pass
    
    def _build_prompt(self, section_text: str, section_key: str = None, heading: str = None) -> str:
        """Build the grounded summarization prompt"""
        prompt = f"""You are analyzing a section of U.S. federal legislation. Your task is to create a grounded summary based ONLY on the provided text.

CRITICAL RULES:
1. Base your summary ONLY on the text provided below
2. Extract 1-3 short quotes (max 25 words each) as evidence for your summary
3. Do NOT invent sponsors, costs, dates, effects, or implications not in the text
4. Use neutral language: "This section does X" not "You should support/oppose"
5. If the text is unclear or insufficient, state "Not enough information in this section text"

SECTION TEXT:
"""
        if section_key:
            prompt += f"Section: {section_key}\n"
        if heading:
            prompt += f"Heading: {heading}\n"
        
        prompt += f"\n{section_text}\n\n"
        
        prompt += """OUTPUT FORMAT (JSON):
{
  "plain_summary_bullets": ["bullet 1", "bullet 2", ...],  // 5-10 bullets max
  "key_terms": ["term1", "term2"],  // Optional: important terms defined
  "who_it_affects": ["group1", "group2"],  // Optional: who this affects
  "evidence_quotes": ["quote1...", "quote2..."],  // 1-3 quotes from text above
  "uncertainties": ["unclear point 1", ...]  // Optional: anything unclear
}

Generate the summary now as valid JSON:"""
        
        return prompt


class OpenAIClient(LLMClient):
    """OpenAI LLM client"""
    
    def __init__(self):
        self.api_key = settings.LLM_API_KEY
        self.model = settings.LLM_MODEL
        self.base_url = settings.LLM_BASE_URL or "https://api.openai.com/v1"
    
    async def generate_summary(self, section_text: str, section_key: str = None, heading: str = None) -> SummarySectionOutput:
        prompt = self._build_prompt(section_text, section_key, heading)
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "You are a precise legislative analyst. Always respond with valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                    "response_format": {"type": "json_object"} if "gpt-4" in self.model or "gpt-3.5" in self.model else None
                }
            )
            response.raise_for_status()
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            # Parse JSON response
            summary_dict = json.loads(content)
            return SummarySectionOutput(**summary_dict)


class AnthropicClient(LLMClient):
    """Anthropic Claude LLM client"""
    
    def __init__(self):
        self.api_key = settings.LLM_API_KEY
        self.model = settings.LLM_MODEL
    
    async def generate_summary(self, section_text: str, section_key: str = None, heading: str = None) -> SummarySectionOutput:
        prompt = self._build_prompt(section_text, section_key, heading)
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "max_tokens": 2000,
                    "temperature": 0.3,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ]
                }
            )
            response.raise_for_status()
            
            result = response.json()
            content = result["content"][0]["text"]
            
            # Parse JSON response
            summary_dict = json.loads(content)
            return SummarySectionOutput(**summary_dict)


class LocalLLMClient(LLMClient):
    """Local LLM client (e.g., via LM Studio, Ollama with OpenAI-compatible API)"""
    
    def __init__(self):
        self.base_url = settings.LLM_BASE_URL
        self.model = settings.LLM_MODEL
    
    async def generate_summary(self, section_text: str, section_key: str = None, heading: str = None) -> SummarySectionOutput:
        prompt = self._build_prompt(section_text, section_key, heading)
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Content-Type": "application/json"},
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "You are a precise legislative analyst. Always respond with valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3
                }
            )
            response.raise_for_status()
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            # Parse JSON response
            summary_dict = json.loads(content)
            return SummarySectionOutput(**summary_dict)


class GroqClient(LLMClient):
    """Groq client - FREE tier with Llama/Mixtral models (OpenAI-compatible)"""
    
    def __init__(self):
        self.api_key = settings.LLM_API_KEY
        self.model = settings.LLM_MODEL or "llama-3.3-70b-versatile"  # Free, powerful model
        self.base_url = "https://api.groq.com/openai/v1"
    
    async def generate_summary(self, section_text: str, section_key: str = None, heading: str = None) -> SummarySectionOutput:
        prompt = self._build_prompt(section_text, section_key, heading)
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Build request - only use json_object mode for supported models
            request_body = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are a precise legislative analyst. Always respond with valid JSON only. No markdown, no explanation, just the JSON object."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 2000
            }
            
            # JSON mode is supported for llama3-groq and some other models
            # But can cause issues with llama-3.1 models, so we skip it
            # The prompt already instructs JSON output
            
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=request_body
            )
            response.raise_for_status()
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            # Parse JSON response - handle potential markdown wrapping
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            summary_dict = json.loads(content)
            return SummarySectionOutput(**summary_dict)


def get_llm_client() -> LLMClient:
    """Factory function to get the configured LLM client"""
    provider = settings.LLM_PROVIDER.lower()
    
    if provider == "openai":
        return OpenAIClient()
    elif provider == "anthropic":
        return AnthropicClient()
    elif provider == "groq":
        return GroqClient()
    elif provider == "local":
        return LocalLLMClient()
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")
