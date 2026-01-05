# Warp Agent Rules for LearnItIn API

## Project Context

This is a FastAPI-based educational platform backend with JWT authentication, SQLAlchemy ORM, and LangChain AI integration.

## Code Style Guidelines

### Python Style
- Follow PEP 8 conventions
- Use type hints for function parameters and return values
- Use async/await for all API endpoints
- Keep functions focused and single-purpose
- Maximum line length: 100 characters

### FastAPI Patterns
- Use dependency injection for database sessions and authentication
- Define Pydantic schemas for request/response validation
- Use APIRouter for endpoint organization
- Include proper HTTP status codes and error messages
- Add docstrings to all endpoints

### Database Guidelines
- Use SQLAlchemy ORM models, not raw SQL
- Always use database sessions from dependency injection
- Commit transactions explicitly
- Handle database errors with proper HTTP exceptions
- Use relationships for foreign keys

### Security Best Practices
- Never log or expose sensitive data (passwords, tokens, API keys)
- Always hash passwords before storing
- Validate and sanitize all user inputs
- Use proper authentication for protected endpoints
- Keep SECRET_KEY and API keys in environment variables

## Project Structure Rules

### Adding New Features

1. **Models**: Create in `app/models/` - Define SQLAlchemy models
2. **Schemas**: Create in `app/schemas/` - Define Pydantic models for validation
3. **Endpoints**: Create in `app/api/v1/` - API routes and handlers
4. **Services**: Create in `app/services/` - Business logic and external integrations
5. **Register**: Add router to `app/main.py`

### File Naming
- Use lowercase with underscores: `user_service.py`
- Model files match table names: `user.py` for User model
- Router files match resource names: `courses.py` for course endpoints

## Common Operations

### Creating New Endpoints

```python
# 1. Define schema in app/schemas/
class ResourceCreate(BaseModel):
    field: str

# 2. Create model in app/models/
class Resource(Base):
    __tablename__ = "resources"
    id = Column(Integer, primary_key=True)
    field = Column(String)

# 3. Create router in app/api/v1/
router = APIRouter()

@router.post("/", response_model=ResourceSchema)
async def create_resource(
    resource: ResourceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # Implementation
    pass

# 4. Register in app/main.py
app.include_router(
    resource.router,
    prefix=f"{settings.API_V1_PREFIX}/resources",
    tags=["Resources"]
)
```

### Running the Application

```bash
# Development server with auto-reload
uvicorn app.main:app --reload

# With specific host and port
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Initialize database
python -m app.db.init_db
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test
pytest tests/test_auth.py -v
```

## Dependencies

### When Adding New Dependencies
1. Install: `pip install package-name`
2. Update requirements: `pip freeze > requirements.txt`
3. Document usage in relevant files

### Core Dependencies
- **fastapi**: Web framework
- **uvicorn**: ASGI server
- **sqlalchemy**: ORM
- **python-dotenv**: Environment variables
- **langchain**: AI integration
- **python-jose**: JWT handling
- **passlib**: Password hashing

## LangChain Integration

### Adding LangChain Features
- Implement in `app/services/langchain_service.py`
- Check for `OPENAI_API_KEY` before making calls
- Handle errors gracefully
- Use async methods
- Document expected behavior

### Example Pattern
```python
async def new_ai_feature(self, input: str) -> str:
    if not settings.OPENAI_API_KEY:
        return "AI features not configured"
    
    template = ChatPromptTemplate.from_messages([
        ("system", "You are..."),
        ("user", "{input}")
    ])
    
    chain = template | self.llm
    response = await chain.ainvoke({"input": input})
    return response.content
```

## Database Operations

### Queries
```python
# Get single record
user = db.query(User).filter(User.id == user_id).first()

# Get multiple records
users = db.query(User).filter(User.is_active == True).all()

# Create record
db_user = User(**user_data.dict())
db.add(db_user)
db.commit()
db.refresh(db_user)

# Update record
db.query(User).filter(User.id == user_id).update({"field": "value"})
db.commit()

# Delete record
db.query(User).filter(User.id == user_id).delete()
db.commit()
```

## Error Handling

### HTTP Exceptions
```python
from fastapi import HTTPException, status

# 400 Bad Request
raise HTTPException(status_code=400, detail="Invalid input")

# 401 Unauthorized
raise HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"}
)

# 404 Not Found
raise HTTPException(status_code=404, detail="Resource not found")
```

## Environment Variables

Always use environment variables for:
- Database credentials
- API keys
- Secret keys
- Configuration that changes between environments

Access via: `os.getenv("VAR_NAME", "default_value")`

## Documentation

### Endpoint Documentation
```python
@router.post(
    "/endpoint",
    response_model=Schema,
    summary="Brief description",
    description="Detailed description of what this endpoint does",
    response_description="Description of response"
)
async def endpoint_name():
    """
    Detailed docstring explaining:
    - Purpose
    - Parameters
    - Returns
    - Raises
    """
    pass
```

## Common Gotchas

1. **Virtual Environment**: Always activate venv before working
2. **Database Sessions**: Always close sessions (handled by dependency injection)
3. **Async/Await**: Use `async def` and `await` consistently
4. **Import Order**: Standard library → Third party → Local imports
5. **Environment File**: Copy `.env.example` to `.env` before running

## Debugging Tips

1. Check FastAPI auto-docs: http://localhost:8000/docs
2. Enable debug mode: Set `DEBUG=True` in `.env`
3. Check logs: Look at console output from uvicorn
4. Database issues: Verify connection string in `.env`
5. Import errors: Ensure all `__init__.py` files exist

## Version Control

### Commits
- Use clear, descriptive commit messages
- Co-author AI contributions: `Co-Authored-By: Warp <agent@warp.dev>`

### Branches
- `main`: Production-ready code
- `develop`: Development branch
- `feature/*`: New features
- `bugfix/*`: Bug fixes

## Performance Considerations

1. Use database connection pooling
2. Implement caching where appropriate
3. Use pagination for list endpoints
4. Avoid N+1 queries
5. Use async operations throughout

## When to Ask for Help

If you encounter:
- Security-related changes
- Database schema migrations
- Architecture decisions
- Performance optimization needs
- Third-party integration issues

Always verify with the developer before proceeding with significant changes.
