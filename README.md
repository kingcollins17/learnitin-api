# LearnItIn API - Feature-First Architecture

A FastAPI application with feature-first (vertical slice) architecture, SQLModel ORM, and async MySQL support.

## 🏗️ Architecture Overview

This project follows a **feature-first architecture** where each feature is self-contained with its own models, schemas, services, repositories, and routes.

### Project Structure

```
app/
├── common/                    # Shared utilities and configuration
│   ├── config.py             # Application settings
│   ├── security.py           # Authentication & password hashing
│   ├── deps.py               # Common FastAPI dependencies
│   └── database/
│       ├── base.py           # SQLModel base configuration
│       ├── session.py        # Async database session management
│       └── init_db.py        # Database initialization
│
├── features/                  # Feature modules (vertical slices)
│   ├── auth/                 # Authentication feature
│   │   ├── models.py         # Auth-specific models (if any)
│   │   ├── schemas.py        # Request/response schemas
│   │   ├── service.py        # Business logic
│   │   └── router.py         # API endpoints
│   │
│   └── users/                # User management feature
│       ├── models.py         # User database model
│       ├── schemas.py        # User schemas
│       ├── repository.py     # Database operations
│       ├── service.py        # Business logic
│       └── router.py         # User endpoints
│
└── main.py                    # Application entry point
```

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- MySQL 8.0+
- pip or poetry

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd learnitin-api
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up MySQL database**
   ```bash
   # Create database
   mysql -u root -p
   CREATE DATABASE learnitin_db;
   exit;
   ```

5. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your MySQL credentials
   ```

   Required environment variables:
   ```env
   DB_HOST=localhost
   DB_PORT=3306
   DB_USER=root
   DB_PASSWORD=your-password
   DB_NAME=learnitin_db
   SECRET_KEY=your-secret-key-here
   ```

6. **Run the application**
   ```bash
   uvicorn app.main:app --reload
   ```

   The API will be available at `http://localhost:8000`
   - API Documentation: `http://localhost:8000/docs`
   - Alternative docs: `http://localhost:8000/redoc`

## 📚 Feature-First Architecture

### What is Feature-First Architecture?

Instead of organizing code by technical layers (models, views, controllers), we organize by **business features**. Each feature is a vertical slice containing everything needed for that functionality.

### Benefits

- **Easier to navigate**: Related code is co-located
- **Better scalability**: Features can be developed independently
- **Clearer boundaries**: Each feature has well-defined responsibilities
- **Simpler testing**: Test entire features in isolation

### Adding a New Feature

To add a new feature (e.g., "courses"):

1. **Create feature directory**
   ```bash
   mkdir -p app/features/courses
   touch app/features/courses/__init__.py
   ```

2. **Create models** (`models.py`)
   ```python
   from sqlmodel import Field, SQLModel
   
   class Course(SQLModel, table=True):
       __tablename__ = "courses"
       id: int | None = Field(default=None, primary_key=True)
       title: str
       description: str
   ```

3. **Create schemas** (`schemas.py`)
   ```python
   from pydantic import BaseModel
   
   class CourseCreate(BaseModel):
       title: str
       description: str
   
   class CourseResponse(BaseModel):
       id: int
       title: str
       description: str
   ```

4. **Create repository** (`repository.py`)
   ```python
   from sqlalchemy.ext.asyncio import AsyncSession
   from sqlmodel import select
   from .models import Course
   
   class CourseRepository:
       def __init__(self, session: AsyncSession):
           self.session = session
       
       async def create(self, course: Course) -> Course:
           self.session.add(course)
           await self.session.flush()
           await self.session.refresh(course)
           return course
   ```

5. **Create service** (`service.py`)
   ```python
   from sqlalchemy.ext.asyncio import AsyncSession
   from .repository import CourseRepository
   from .schemas import CourseCreate
   from .models import Course
   
   class CourseService:
       def __init__(self, session: AsyncSession):
           self.repository = CourseRepository(session)
       
       async def create_course(self, data: CourseCreate) -> Course:
           course = Course(**data.model_dump())
           return await self.repository.create(course)
   ```

6. **Create router** (`router.py`)
   ```python
   from fastapi import APIRouter, Depends
   from sqlalchemy.ext.asyncio import AsyncSession
   from app.common.database.session import get_async_session
   from .service import CourseService
   from .schemas import CourseCreate, CourseResponse
   
   router = APIRouter()
   
   @router.post("/", response_model=CourseResponse)
   async def create_course(
       data: CourseCreate,
       session: AsyncSession = Depends(get_async_session)
   ):
       service = CourseService(session)
       return await service.create_course(data)
   ```

7. **Register router in main.py**
   ```python
   from app.features.courses.router import router as courses_router
   
   app.include_router(
       courses_router,
       prefix=f"{settings.API_V1_PREFIX}/courses",
       tags=["Courses"]
   )
   ```

8. **Import model in session.py** (for table creation)
   ```python
   # In app/common/database/session.py, add to init_db():
   from app.features.courses.models import Course  # noqa: F401
   ```

## 🗄️ Database

### SQLModel + Async MySQL

This project uses:
- **SQLModel**: Combines SQLAlchemy and Pydantic for type-safe ORM
- **asyncmy**: Async MySQL driver for non-blocking database operations
- **AsyncSession**: Async database sessions for better performance

### Database Session Management

Sessions are managed automatically via dependency injection:

```python
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.database.session import get_async_session

@router.get("/")
async def my_endpoint(session: AsyncSession = Depends(get_async_session)):
    # Session is automatically created, committed, and closed
    result = await session.execute(select(User))
    return result.scalars().all()
```

### Migrations

For production, consider using Alembic for database migrations:

```bash
pip install alembic
alembic init alembic
# Configure alembic.ini and env.py
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

## 🔐 Authentication

The API uses JWT (JSON Web Tokens) for authentication:

1. **Register**: `POST /api/v1/auth/register`
2. **Login**: `POST /api/v1/auth/login` (returns access token)
3. **Use token**: Include in `Authorization: Bearer <token>` header

Protected endpoints use the `get_current_user` or `get_current_active_user` dependency.

## 🧪 Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest
```

## 📝 API Documentation

Once running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 🔧 Development

### Code Style

- Use `black` for formatting
- Use `ruff` for linting
- Type hints are required

### Environment Variables

See `.env.example` for all available configuration options.

## 📦 Deployment

1. Set `DEBUG=False` in production
2. Use a strong `SECRET_KEY`
3. Configure proper CORS origins
4. Use environment-specific database credentials
5. Consider using a process manager like `gunicorn` with `uvicorn` workers:

```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

## 📄 License

[Your License Here]
