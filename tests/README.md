# Testing Guide

## Running Tests

### Run all tests
```bash
pytest
```

### Run with coverage
```bash
pytest --cov=app --cov-report=html
```

### Run specific feature tests
```bash
# Auth tests only
pytest tests/features/auth/ -v

# Users tests only
pytest tests/features/users/ -v
```

### Run by markers
```bash
# Run only auth tests
pytest -m auth

# Run only users tests
pytest -m users

# Run integration tests
pytest -m integration
```

### Run specific test class or function
```bash
# Run specific test class
pytest tests/features/auth/test_auth.py::TestAuthRegistration

# Run specific test
pytest tests/features/auth/test_auth.py::TestAuthRegistration::test_register_new_user
```

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── features/
│   ├── auth/
│   │   └── test_auth.py     # Auth feature tests
│   └── users/
│       └── test_users.py    # Users feature tests
└── utils/
    └── factories.py         # Test data generators
```

## Writing New Tests

### 1. Create test file for new feature

```python
# tests/features/my_feature/test_my_feature.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_my_feature(client: AsyncClient):
    response = await client.get("/api/v1/my-endpoint")
    assert response.status_code == 200
```

### 2. Use existing fixtures

Available fixtures:
- `client` - Async HTTP client
- `db_session` - Database session
- `test_user_data` - Sample user data
- `created_user` - Pre-created test user
- `auth_token` - JWT token
- `auth_headers` - Authorization headers

### 3. Add custom fixtures

Add to `conftest.py` or create feature-specific conftest:

```python
@pytest.fixture
async def my_custom_fixture(db_session):
    # Setup
    yield data
    # Teardown
```

## Test Database

Tests use a separate test database: `test_{DB_NAME}`

- Database is created before tests
- Tables are created from SQLModel metadata
- Each test gets a fresh session
- Database is dropped after all tests

## Coverage

View coverage report:
```bash
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

## Best Practices

1. **Use async/await** for all async operations
2. **Mark tests** with appropriate markers (@pytest.mark.auth, etc.)
3. **Use fixtures** for common setup
4. **Test edge cases** and error conditions
5. **Keep tests isolated** - no dependencies between tests
6. **Use descriptive names** - test names should explain what they test
