"""Tests for LangChain service."""
import pytest
from pydantic import BaseModel, Field
from typing import List

from app.services.langchain_service import LangChainService


class SimpleResponse(BaseModel):
    """Simple test response schema."""
    answer: str = Field(description="The answer")
    confidence: float = Field(description="Confidence score 0-1")


class TestLangChainService:
    """Test suite for LangChain service."""
    
    @pytest.fixture
    def service(self):
        """Create a LangChain service instance."""
        return LangChainService(backend="gemini", temperature=0.5)
    
    @pytest.mark.asyncio
    async def test_basic_invoke(self, service):
        """Test basic text generation."""
        response = await service.invoke(
            system_prompt="You are a helpful assistant.",
            user_prompt="Say 'Hello, World!' and nothing else."
        )
        
        assert isinstance(response, str)
        assert len(response) > 0
    
    @pytest.mark.asyncio
    async def test_structured_output(self, service):
        """Test structured output with Pydantic model."""
        response = await service.invoke(
            system_prompt="You are a helpful assistant.",
            user_prompt="What is 2+2? Provide your answer and confidence.",
            response_schema=SimpleResponse
        )
        
        assert isinstance(response, SimpleResponse)
        assert isinstance(response.answer, str)
        assert isinstance(response.confidence, float)
        assert 0 <= response.confidence <= 1
    
    @pytest.mark.asyncio
    async def test_invoke_with_context(self, service):
        """Test context-based invocation."""
        context = "The user is a beginner programmer."
        
        response = await service.invoke_with_context(
            system_prompt="You are a programming tutor.",
            user_prompt="Explain variables.",
            context=context
        )
        
        assert isinstance(response, str)
        assert len(response) > 0
    
    def test_invalid_backend(self):
        """Test that invalid backend raises error."""
        with pytest.raises(ValueError, match="Unsupported backend"):
            LangChainService(backend="invalid_backend")
    
    def test_gemini_without_api_key(self, monkeypatch):
        """Test that Gemini without API key raises error."""
        # Temporarily remove the API key
        from app.common import config
        monkeypatch.setattr(config.settings, "GEMINI_API_KEY", "")
        
        with pytest.raises(ValueError, match="GEMINI_API_KEY not configured"):
            LangChainService(backend="gemini")
