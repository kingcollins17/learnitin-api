from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from app.core.config import settings

class LangChainService:
    """Service for LangChain operations."""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model="gpt-4",
            temperature=0.7
        )
    
    async def generate_response(self, prompt: str, context: str = "") -> str:
        """Generate a response using LangChain."""
        if not settings.OPENAI_API_KEY:
            return "OpenAI API key not configured"
        
        template = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful educational assistant for LearnItIn platform."),
            ("user", "{context}\n\n{prompt}")
        ])
        
        chain = template | self.llm
        response = await chain.ainvoke({"context": context, "prompt": prompt})
        
        return response.content
    
    async def create_learning_plan(self, topic: str, level: str) -> str:
        """Create a personalized learning plan."""
        prompt = f"Create a learning plan for {topic} at {level} level."
        return await self.generate_response(prompt)

# Singleton instance
langchain_service = LangChainService()
