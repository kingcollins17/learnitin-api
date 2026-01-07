# LearnItIn API - Architecture & Code Style Guide

## Project Architecture

### Architecture Pattern: Feature-First (Vertical Slice)

This project follows a **feature-first architecture** where code is organized by business features rather than technical layers.

**Technology Stack:**
- **FastAPI** + **Python 3.13** - Modern async web framework
- **SQLModel** + **MySQL 8.0** - Type-safe ORM with async support
- **Argon2** - Modern password hashing (OWASP recommended)
- **JWT** - Stateless authentication
- **pytest** - Async testing with coverage
- **LangChain** + **Google Gemini** - AI-powered features

**Project Structure:**
```
app/
├── common/          # Shared utilities (config, security, database, responses)
├── features/        # Feature modules (auth, users, courses, etc.)
│   └── {feature}/
│       ├── models.py      # SQLModel database models
│       ├── schemas.py     # Pydantic request/response
│       ├── repository.py  # Data access layer
│       ├── service.py     # Business logic
│       └── router.py      # API endpoints
└── main.py         # Application entry point
```

## Feature Module Pattern

Each feature is self-contained with:
1. **Models** - SQLModel with `table=True`
2. **Schemas** - Pydantic for validation
3. **Repository** - Async database operations
4. **Service** - Business logic
5. **Router** - FastAPI endpoints

## API Response Structure

All API endpoints return responses wrapped in a generic `ApiResponse[T]` structure for consistency.

### Response Format

```python
class ApiResponse(BaseModel, Generic[T]):
    status_code: int      # HTTP status code
    details: str          # Human-readable message
    data: Optional[T]     # Response data (typed)
```

### Success Response Example

```json
{
  "status_code": 200,
  "details": "User retrieved successfully",
  "data": {
    "id": 1,
    "email": "user@example.com",
    "username": "john_doe"
  }
}
```

### Error Response Example

```json
{
  "status_code": 404,
  "details": "User not found",
  "data": null
}
```

### Usage in Endpoints

```python
from app.common.responses import ApiResponse, success_response

@router.get("/users/me", response_model=ApiResponse[UserResponse])
async def get_current_user(current_user: User = Depends(get_current_active_user)):
    return success_response(
        data=current_user,
        details="User retrieved successfully"
    )
```

**Helper Functions:**
- `success_response(data, details, status_code)` - Create success response
- `error_response(details, status_code, data)` - Create error response

## Coding Standards

- **Type hints required** for all functions
- **Async/await** for all I/O operations
- **Dependency injection** for sessions and auth
- **Pydantic validation** for all inputs
- **Argon2** for password hashing (no length limits)
- **Generic responses** for all API endpoints
- **Error handling** - All endpoints must use try-catch blocks:
  ```python
  try:
      # Endpoint logic
      return success_response(data=result, details="Success")
  except HTTPException:
      raise  # Re-raise HTTP exceptions as-is
  except Exception as e:
      # Convert other exceptions to HTTP 500
      raise HTTPException(
          status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
          detail=f"Operation failed: {str(e)}"
      )
  ```


## Development

```bash
make dev        # Start development server
make test       # Run tests
make test-cov   # Run tests with coverage
```

See [README.md](../README.md) for full documentation.

