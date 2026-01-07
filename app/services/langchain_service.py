"""LangChain service for AI operations with flexible backend support."""
from typing import Any, Optional, Type, TypeVar, List
from pydantic import BaseModel
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import BaseTool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from app.common.config import settings


T = TypeVar("T", bound=BaseModel)


class LangChainService:
    """
    Flexible LangChain service supporting multiple backends.
    
    Features:
    - Multiple backend support (Google Gemini, OpenAI)
    - Structured output with Pydantic models
    - Custom system and user prompts
    - Tool integration support
    - Async operations
    """
    
    def __init__(
        self,
        backend: str = "gemini",
        model: Optional[str] = None,
        temperature: float = 0.7,
    ):
        """
        Initialize LangChain service with specified backend.
        
        Args:
            backend: Backend to use ("gemini" or "openai")
            model: Model name (defaults to backend-specific default)
            temperature: Model temperature (0.0-1.0)
        """
        self.backend = backend
        self.temperature = temperature
        self.llm = self._initialize_llm(backend, model, temperature)
    
    def _initialize_llm(
        self,
        backend: str,
        model: Optional[str],
        temperature: float,
    ) -> BaseChatModel:
        """Initialize the language model based on backend."""
        if backend == "gemini":
            if not settings.GEMINI_API_KEY:
                raise ValueError("GEMINI_API_KEY not configured in environment")
            
            return ChatGoogleGenerativeAI(
                model=model or "gemini-2.5-flash",
                google_api_key=settings.GEMINI_API_KEY,
                temperature=temperature,
            )
        
        elif backend == "openai":
            if not settings.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY not configured in environment")
            
            return ChatOpenAI(
                api_key=settings.OPENAI_API_KEY,
                model=model or "gpt-4",
                temperature=temperature,
            )
        
        else:
            raise ValueError(f"Unsupported backend: {backend}")
    
    async def invoke(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: Optional[Type[T]] = None,
        tools: Optional[List[BaseTool]] = None,
        **kwargs: Any,
    ) -> T | str:
        """
        Invoke the LLM with custom prompts and optional structured output.
        
        Args:
            system_prompt: System/master prompt defining AI behavior
            user_prompt: User's input prompt
            response_schema: Optional Pydantic model for structured output
            tools: Optional list of LangChain tools to attach
            **kwargs: Additional variables for prompt formatting
            
        Returns:
            Structured response (if schema provided) or string response
            
        Example:
            ```python
            class Answer(BaseModel):
                answer: str
                confidence: float
            
            result = await service.invoke(
                system_prompt="You are a helpful assistant",
                user_prompt="What is 2+2?",
                response_schema=Answer
            )
            ```
        """
        # Create prompt template
        template = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", user_prompt),
        ])
        
        # Build the chain
        llm: Any = self.llm
        
        # Bind tools if provided
        if tools:
            llm = llm.bind_tools(tools)
        
        # Add structured output if schema provided
        if response_schema:
            llm = llm.with_structured_output(response_schema)
        
        # Create and invoke chain
        chain = template | llm
        
        # Invoke with any additional kwargs for prompt variables
        response: Any = await chain.ainvoke(kwargs if kwargs else {})
        
        # Return structured response or content
        if response_schema:
            return response  # type: ignore[return-value]
        else:
            # For non-structured responses, extract content
            return response.content if hasattr(response, "content") else str(response)
    
    async def invoke_with_context(
        self,
        system_prompt: str,
        user_prompt: str,
        context: str,
        response_schema: Optional[Type[T]] = None,
        tools: Optional[List[BaseTool]] = None,
    ) -> T | str:
        """
        Invoke with additional context.
        
        Args:
            system_prompt: System/master prompt
            user_prompt: User's input prompt
            context: Additional context to include
            response_schema: Optional Pydantic model for structured output
            tools: Optional list of LangChain tools
            
        Returns:
            Structured response or string
        """
        # Combine context with user prompt
        full_user_prompt = f"Context:\n{context}\n\nQuery:\n{user_prompt}"
        
        return await self.invoke(
            system_prompt=system_prompt,
            user_prompt=full_user_prompt,
            response_schema=response_schema,
            tools=tools,
        )


# Singleton instance with Gemini backend (default)
langchain_service = LangChainService(backend="gemini")
