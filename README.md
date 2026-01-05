# LearnItIn API

A modern FastAPI backend for the LearnItIn educational platform with JWT authentication, SQLAlchemy ORM, and LangChain integration.

## Features

- ⚡ **FastAPI** - High-performance async Python web framework
- 🔐 **JWT Authentication** - Secure token-based authentication
- 💾 **SQLAlchemy ORM** - Database abstraction and management
- 🤖 **LangChain Integration** - AI-powered educational features
- 📝 **OpenAPI Documentation** - Auto-generated API docs
- 🔒 **Security** - Password hashing with bcrypt
- 🌍 **CORS Enabled** - Cross-origin resource sharing configured
- 📦 **Virtual Environment** - Isolated Python dependencies

## Project Structure

```
learnitin-api/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── auth.py          # Authentication endpoints
│   │       └── users.py         # User management endpoints
│   ├── core/
│   │   ├── config.py            # Application configuration
│   │   ├── security.py          # JWT and password utilities
│   │   └── deps.py              # FastAPI dependencies
│   ├── db/
│   │   ├── session.py           # Database session management
│   │   └── init_db.py           # Database initialization
│   ├── models/
│   │   └── user.py              # SQLAlchemy models
│   ├── schemas/
│   │   ├── user.py              # User Pydantic schemas
│   │   └── auth.py              # Auth Pydantic schemas
│   ├── services/
│   │   └── langchain_service.py # LangChain AI services
│   └── main.py                  # Application entry point
├── tests/                       # Test directory
├── docs/                        # Documentation
├── venv/                        # Virtual environment
├── .env                         # Environment variables (create from .env.example)
├── .env.example                 # Environment template
├── .gitignore                   # Git ignore rules
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## Getting Started

### Prerequisites

- Python 3.9+
- pip
- virtualenv (or python3-venv)

### Installation

1. **Navigate to the project directory:**
```bash
cd learnitin-api
```

2. **Activate the virtual environment:**
```bash
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows
```

3. **Create environment file:**
```bash
cp .env.example .env
```

4. **Edit `.env` file and add your configurations:**
- Set a strong `SECRET_KEY`
- Add your `OPENAI_API_KEY` for LangChain features
- Configure database URL if not using SQLite

5. **Initialize the database:**
```bash
python -m app.db.init_db
```

6. **Run the development server:**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running, access the interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register a new user
- `POST /api/v1/auth/login` - Login and get access token

### Users
- `GET /api/v1/users/me` - Get current user info (requires auth)
- `GET /api/v1/users/{user_id}` - Get user by ID (requires auth)

### Health Check
- `GET /` - Root endpoint with API info
- `GET /health` - Health check endpoint

## Authentication Flow

1. **Register a new user:**
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "testuser",
    "password": "securepassword123",
    "full_name": "Test User"
  }'
```

2. **Login to get access token:**
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=securepassword123"
```

3. **Use the token in subsequent requests:**
```bash
curl -X GET "http://localhost:8000/api/v1/users/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Development

### Running Tests
```bash
pytest tests/
```

### Code Formatting
```bash
black app/
```

### Type Checking
```bash
mypy app/
```

## Environment Variables

See `.env.example` for all available configuration options:

- `APP_NAME` - Application name
- `APP_VERSION` - Application version
- `DEBUG` - Debug mode (True/False)
- `SECRET_KEY` - JWT secret key
- `DATABASE_URL` - Database connection string
- `OPENAI_API_KEY` - OpenAI API key for LangChain
- `ACCESS_TOKEN_EXPIRE_MINUTES` - JWT token expiration time

## LangChain Integration

The project includes a `LangChainService` for AI-powered features:

```python
from app.services.langchain_service import langchain_service

# Generate educational content
response = await langchain_service.generate_response(
    prompt="Explain Python decorators",
    context="Beginner level"
)

# Create learning plans
plan = await langchain_service.create_learning_plan(
    topic="Python",
    level="intermediate"
)
```

## Security Notes

⚠️ **Important Security Reminders:**

1. Always use a strong, unique `SECRET_KEY` in production
2. Never commit `.env` file to version control
3. Use HTTPS in production
4. Regularly update dependencies
5. Use environment-specific configurations
6. Implement rate limiting for production
7. Keep OpenAI API keys secure

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For issues and questions, please open an issue on the repository.
