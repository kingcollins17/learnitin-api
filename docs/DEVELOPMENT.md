# Development Guide

## Setup Development Environment

### Prerequisites
- Python 3.9+
- Git
- Code editor (VS Code recommended)

### Initial Setup

1. Clone and navigate to project:
```bash
cd learnitin-api
```

2. Activate virtual environment:
```bash
source venv/bin/activate
```

3. Install development dependencies:
```bash
pip install pytest black mypy flake8 pytest-cov httpx
```

4. Set up pre-commit hooks (optional):
```bash
pip install pre-commit
pre-commit install
```

## Project Architecture

### Folder Structure

```
app/
├── api/v1/          # API endpoints (versioned)
├── core/            # Core functionality (config, security)
├── db/              # Database configuration
├── models/          # SQLAlchemy models
├── schemas/         # Pydantic schemas
└── services/        # Business logic services
```

### Design Patterns

- **Repository Pattern**: Database access abstraction
- **Dependency Injection**: FastAPI's dependency system
- **Service Layer**: Business logic separation
- **Schema Validation**: Pydantic models

## Adding New Features

### 1. Create a New Model

```python
# app/models/course.py
from sqlalchemy import Column, Integer, String, Text
from app.db.session import Base

class Course(Base):
    __tablename__ = "courses"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text)
```

### 2. Create Schemas

```python
# app/schemas/course.py
from pydantic import BaseModel

class CourseBase(BaseModel):
    title: str
    description: str

class CourseCreate(CourseBase):
    pass

class Course(CourseBase):
    id: int
    
    class Config:
        from_attributes = True
```

### 3. Create API Endpoints

```python
# app/api/v1/courses.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.course import Course
from app.schemas.course import Course as CourseSchema, CourseCreate

router = APIRouter()

@router.post("/", response_model=CourseSchema)
async def create_course(
    course: CourseCreate,
    db: Session = Depends(get_db)
):
    db_course = Course(**course.dict())
    db.add(db_course)
    db.commit()
    db.refresh(db_course)
    return db_course
```

### 4. Register Router

```python
# app/main.py
from app.api.v1 import courses

app.include_router(
    courses.router,
    prefix=f"{settings.API_V1_PREFIX}/courses",
    tags=["Courses"]
)
```

## Testing

### Unit Tests

Create tests in `tests/` directory:

```python
# tests/test_auth.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_register_user():
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "username": "testuser",
            "password": "testpass123"
        }
    )
    assert response.status_code == 200
    assert "id" in response.json()
```

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_auth.py

# Run with verbose output
pytest -v
```

## Code Quality

### Formatting with Black

```bash
# Format all files
black app/

# Check without modifying
black app/ --check
```

### Linting with Flake8

```bash
flake8 app/
```

### Type Checking with MyPy

```bash
mypy app/
```

## Database Migrations

### Using Alembic (Recommended for Production)

1. Install Alembic:
```bash
pip install alembic
```

2. Initialize:
```bash
alembic init alembic
```

3. Configure `alembic/env.py`:
```python
from app.db.session import Base
from app.models.user import User  # Import all models
target_metadata = Base.metadata
```

4. Create migration:
```bash
alembic revision --autogenerate -m "Add courses table"
```

5. Apply migration:
```bash
alembic upgrade head
```

6. Rollback:
```bash
alembic downgrade -1
```

## Debugging

### VS Code Launch Configuration

Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "app.main:app",
        "--reload"
      ],
      "jinja": true,
      "justMyCode": true
    }
  ]
}
```

### Print Debugging

```python
import logging
logger = logging.getLogger(__name__)

@router.get("/debug")
async def debug_endpoint():
    logger.info("Debug information")
    logger.error("Error occurred")
    return {"status": "ok"}
```

### Interactive Debugging

```python
import pdb; pdb.set_trace()  # Python debugger
```

## Working with LangChain

### Example: Adding a New LangChain Feature

```python
# app/services/langchain_service.py

async def summarize_content(self, content: str) -> str:
    """Summarize educational content."""
    prompt = f"Summarize the following content in 3 key points:\n\n{content}"
    return await self.generate_response(prompt)
```

### Using in Endpoints

```python
# app/api/v1/content.py
from app.services.langchain_service import langchain_service

@router.post("/summarize")
async def summarize(content: str):
    summary = await langchain_service.summarize_content(content)
    return {"summary": summary}
```

## Environment Management

### Multiple Environments

Create separate env files:
- `.env.development`
- `.env.staging`
- `.env.production`

Load based on environment:
```python
import os
env = os.getenv("ENV", "development")
load_dotenv(f".env.{env}")
```

## Performance Profiling

### Using cProfile

```bash
python -m cProfile -o output.prof -m uvicorn app.main:app
```

### Analyze with snakeviz

```bash
pip install snakeviz
snakeviz output.prof
```

## Common Tasks

### Add New Dependency

```bash
pip install package-name
pip freeze > requirements.txt
```

### Reset Database

```bash
rm learnitin.db
python -m app.db.init_db
```

### Generate API Client

```bash
# OpenAPI spec available at /openapi.json
curl http://localhost:8000/openapi.json > openapi.json
```

## Git Workflow

```bash
# Create feature branch
git checkout -b feature/new-feature

# Make changes and commit
git add .
git commit -m "Add new feature"

# Push and create PR
git push origin feature/new-feature
```

## Troubleshooting

### Import Errors
- Ensure virtual environment is activated
- Check `PYTHONPATH` includes project root
- Verify all `__init__.py` files exist

### Database Locked (SQLite)
- Close all connections
- Use PostgreSQL for multi-user scenarios

### Port Already in Use
```bash
# Find and kill process on port 8000
lsof -ti:8000 | xargs kill -9
```

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [LangChain Documentation](https://python.langchain.com/)
