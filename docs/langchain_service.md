# LangChain Service

A flexible LangChain service for the LearnItIn API that supports multiple AI backends with structured output capabilities.

## Features

- **Multiple Backend Support**: Google Gemini (default) and OpenAI
- **Structured Output**: Type-safe responses using Pydantic models
- **Tool Integration**: Attach LangChain tools for enhanced capabilities
- **Async Operations**: Full async/await support
- **Type Safety**: Complete type hints throughout

## Quick Start

### Basic Usage

```python
from app.services.langchain_service import langchain_service

# Simple text generation
response = await langchain_service.invoke(
    system_prompt="You are a helpful educational assistant.",
    user_prompt="Explain what Python is in one sentence."
)
print(response)
```

### Structured Output

```python
from pydantic import BaseModel, Field
from typing import List

class LearningPlan(BaseModel):
    topic: str
    duration_weeks: int
    modules: List[str]

# Get structured response
plan: LearningPlan = await langchain_service.invoke(
    system_prompt="You are a curriculum designer.",
    user_prompt="Create a learning plan for Python basics.",
    response_schema=LearningPlan
)

print(f"Topic: {plan.topic}")
print(f"Duration: {plan.duration_weeks} weeks")
```

### With Context

```python
context = """
User Profile:
- Level: Beginner
- Interests: Web Development
- Time: 10 hours/week
"""

response = await langchain_service.invoke_with_context(
    system_prompt="You are a personalized learning advisor.",
    user_prompt="What should I learn next?",
    context=context
)
```

### With Tools

```python
from langchain_core.tools import tool

@tool
def calculate_hours(hours_per_day: int, days: int) -> int:
    """Calculate total study hours."""
    return hours_per_day * days

response = await langchain_service.invoke(
    system_prompt="You are a study planner.",
    user_prompt="Calculate study hours for 2 hours/day for 30 days.",
    tools=[calculate_hours]
)
```

## Configuration

### Environment Variables

Add to your `.env` file:

```env
# For Google Gemini (default)
GEMINI_API_KEY=your_gemini_api_key_here

# For OpenAI (optional)
OPENAI_API_KEY=your_openai_api_key_here
```

### Custom Backend

```python
from app.services.langchain_service import LangChainService

# Use OpenAI instead
service = LangChainService(
    backend="openai",
    model="gpt-4",
    temperature=0.7
)

# Use different Gemini model
service = LangChainService(
    backend="gemini",
    model="gemini-1.5-pro",
    temperature=0.5
)
```

## API Reference

### `LangChainService`

#### `__init__(backend, model, temperature)`

Initialize the service.

**Parameters:**
- `backend` (str): Backend to use ("gemini" or "openai"). Default: "gemini"
- `model` (str, optional): Model name. Defaults to backend-specific default
- `temperature` (float): Model temperature (0.0-1.0). Default: 0.7

#### `async invoke(system_prompt, user_prompt, response_schema, tools, **kwargs)`

Invoke the LLM with custom prompts.

**Parameters:**
- `system_prompt` (str): System/master prompt defining AI behavior
- `user_prompt` (str): User's input prompt
- `response_schema` (Type[BaseModel], optional): Pydantic model for structured output
- `tools` (List[BaseTool], optional): LangChain tools to attach
- `**kwargs`: Additional variables for prompt formatting

**Returns:**
- Structured response (if schema provided) or string

#### `async invoke_with_context(system_prompt, user_prompt, context, response_schema, tools)`

Invoke with additional context.

**Parameters:**
- `system_prompt` (str): System/master prompt
- `user_prompt` (str): User's input prompt
- `context` (str): Additional context to include
- `response_schema` (Type[BaseModel], optional): Pydantic model for structured output
- `tools` (List[BaseTool], optional): LangChain tools

**Returns:**
- Structured response or string

## Examples

See `examples/langchain_usage.py` for comprehensive examples including:
- Basic text generation
- Structured output with Pydantic
- Tool integration
- Context-based invocation
- Multiple backends
- Complex nested schemas

Run examples:
```bash
python -m examples.langchain_usage
```

## Testing

Run tests:
```bash
pytest tests/test_langchain_service.py -v
```

## Architecture

The service follows the project's feature-first architecture:

```
app/services/
└── langchain_service.py    # Main service implementation

examples/
└── langchain_usage.py      # Usage examples

tests/
└── test_langchain_service.py  # Test suite
```

## Best Practices

1. **Use Structured Output**: Define Pydantic models for type-safe responses
2. **Set Appropriate Temperature**: Lower (0.0-0.3) for factual, higher (0.7-1.0) for creative
3. **Provide Clear Prompts**: Be specific in system and user prompts
4. **Handle Errors**: Wrap calls in try-except for production use
5. **Use Context**: Provide relevant context for better responses

## Troubleshooting

### "GEMINI_API_KEY not configured"

Make sure you have set `GEMINI_API_KEY` in your `.env` file.

### Type Hints Warnings

The service uses `Any` type hints for LangChain's dynamic types. This is intentional to maintain flexibility while providing type safety where possible.

### Structured Output Not Working

Ensure your Pydantic model has proper field descriptions using `Field(description="...")` as this helps the LLM understand what to generate.

## License

Part of the LearnItIn API project.
