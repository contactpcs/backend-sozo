"""AI Module - LLM abstraction layer."""
from abc import ABC, abstractmethod
from typing import Optional, List
from dataclasses import dataclass
import logging


logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """LLM API response."""
    
    content: str
    model: str
    tokens_used: int
    provider: str


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.7
    ) -> LLMResponse:
        """Generate content from LLM."""
        pass
    
    @abstractmethod
    async def summarize(
        self,
        text: str,
        max_length: int = 500
    ) -> str:
        """Summarize provided text."""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider implementation."""
    
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.api_key = api_key
        self.model = model
    
    async def generate(
        self,
        prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.7
    ) -> LLMResponse:
        """Generate content using OpenAI API."""
        try:
            import openai
            
            openai.api_key = self.api_key
            
            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            return LLMResponse(
                content=response.choices[0].message.content,
                model=self.model,
                tokens_used=response.usage.total_tokens,
                provider="openai"
            )
        
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise
    
    async def summarize(self, text: str, max_length: int = 500) -> str:
        """Summarize text using OpenAI."""
        prompt = f"Summarize the following text in {max_length} characters or less:\n\n{text}"
        response = await self.generate(prompt, max_tokens=max_length // 4)
        return response.content


class AzureOpenAIProvider(LLMProvider):
    """Azure OpenAI provider implementation."""
    
    def __init__(
        self,
        api_key: str,
        endpoint: str,
        deployment: str,
        api_version: str = "2023-05-15"
    ):
        self.api_key = api_key
        self.endpoint = endpoint
        self.deployment = deployment
        self.api_version = api_version
    
    async def generate(
        self,
        prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.7
    ) -> LLMResponse:
        """Generate content using Azure OpenAI."""
        try:
            import openai
            
            openai.api_type = "azure"
            openai.api_base = self.endpoint
            openai.api_version = self.api_version
            openai.api_key = self.api_key
            
            response = await openai.ChatCompletion.acreate(
                engine=self.deployment,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            return LLMResponse(
                content=response.choices[0].message.content,
                model=self.deployment,
                tokens_used=response.usage.total_tokens,
                provider="azure_openai"
            )
        
        except Exception as e:
            logger.error(f"Azure OpenAI API error: {str(e)}")
            raise
    
    async def summarize(self, text: str, max_length: int = 500) -> str:
        """Summarize text using Azure OpenAI."""
        prompt = f"Summarize the following text in {max_length} characters or less:\n\n{text}"
        response = await self.generate(prompt, max_tokens=max_length // 4)
        return response.content


class ClaudeProvider(LLMProvider):
    """Anthropic Claude provider implementation."""
    
    def __init__(self, api_key: str, model: str = "claude-3-sonnet-20240229"):
        self.api_key = api_key
        self.model = model
    
    async def generate(
        self,
        prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.7
    ) -> LLMResponse:
        """Generate content using Claude API."""
        try:
            import anthropic
            
            client = anthropic.AsyncAnthropic(api_key=self.api_key)
            
            message = await client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return LLMResponse(
                content=message.content[0].text,
                model=self.model,
                tokens_used=message.usage.input_tokens + message.usage.output_tokens,
                provider="claude"
            )
        
        except Exception as e:
            logger.error(f"Claude API error: {str(e)}")
            raise
    
    async def summarize(self, text: str, max_length: int = 500) -> str:
        """Summarize text using Claude."""
        prompt = f"Summarize the following text in {max_length} characters or less:\n\n{text}"
        response = await self.generate(prompt, max_tokens=max_length // 4)
        return response.content


class LLMFactory:
    """Factory for creating LLM providers."""
    
    @staticmethod
    def create_provider(
        provider_type: str,
        **kwargs
    ) -> LLMProvider:
        """Create LLM provider instance."""
        if provider_type == "openai":
            return OpenAIProvider(**kwargs)
        elif provider_type == "azure_openai":
            return AzureOpenAIProvider(**kwargs)
        elif provider_type == "claude":
            return ClaudeProvider(**kwargs)
        else:
            raise ValueError(f"Unknown LLM provider: {provider_type}")


class DocumentSummarizer:
    """Document summarization service using LLM."""
    
    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider
    
    async def summarize_clinical_document(
        self,
        document_text: str,
        document_type: str = "general"
    ) -> str:
        """Summarize clinical document with context-aware prompting."""
        if document_type == "assessment":
            prompt = (
                "As a medical professional, summarize the following clinical assessment "
                "focusing on key findings, diagnoses, and recommendations:\n\n" + document_text
            )
        elif document_type == "lab_report":
            prompt = (
                "Summarize the following lab report highlighting abnormal values "
                "and clinical significance:\n\n" + document_text
            )
        else:
            prompt = f"Summarize the following document:\n\n{document_text}"
        
        response = await self.llm.generate(prompt, max_tokens=1000)
        return response.content
    
    async def extract_key_findings(self, document_text: str) -> List[str]:
        """Extract key findings from document."""
        prompt = (
            "Extract the 5 most important clinical findings from the following document. "
            "Return as a numbered list:\n\n" + document_text
        )
        response = await self.llm.generate(prompt, max_tokens=500)
        
        # Parse response into list
        findings = [f.strip() for f in response.content.split("\n") if f.strip()]
        return findings
