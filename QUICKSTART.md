# Quick Start Guide

Get your LearnItIn API up and running in 5 minutes!

## 1. Setup Environment

```bash
# Navigate to project
cd learnitin-api

# Activate virtual environment
source venv/bin/activate

# Verify installation
pip list | grep fastapi
```

## 2. Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and update:
# - SECRET_KEY (generate with: python -c "import secrets; print(secrets.token_urlsafe(32))")
# - OPENAI_API_KEY (if using LangChain features)
```

## 3. Initialize Database

```bash
python -m app.db.init_db
```

Expected output: `Database initialized successfully!`

## 4. Start the Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 5. Test the API

Open your browser to:
- **API Docs**: http://localhost:8000/docs
- **Root**: http://localhost:8000/

### Or use curl:

```bash
# Health check
curl http://localhost:8000/health

# Register a user
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "testuser",
    "password": "testpass123",
    "full_name": "Test User"
  }'

# Login
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=testpass123"

# Get current user (replace TOKEN with your access_token)
curl -X GET "http://localhost:8000/api/v1/users/me" \
  -H "Authorization: Bearer TOKEN"
```

## Next Steps

- Read the [README.md](README.md) for full documentation
- Check [docs/API.md](docs/API.md) for API reference
- See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for development guide
- Review [.warp/rules.md](.warp/rules.md) for Warp Agent guidelines

## Troubleshooting

**Virtual environment not activated?**
```bash
source venv/bin/activate
```

**Port 8000 already in use?**
```bash
# Use a different port
uvicorn app.main:app --reload --port 8001
```

**Database errors?**
```bash
# Reset database
rm learnitin.db
python -m app.db.init_db
```

**Import errors?**
```bash
# Verify you're in the right directory
pwd  # Should show: .../learnitin-api

# Check Python can find the app module
python -c "import app; print('OK')"
```

## Common Commands

```bash
# Activate venv
source venv/bin/activate

# Deactivate venv
deactivate

# Run server
uvicorn app.main:app --reload

# Initialize database
python -m app.db.init_db

# Install new package
pip install package-name
pip freeze > requirements.txt

# Run tests (after installing pytest)
pytest
```

Happy coding! 🚀
