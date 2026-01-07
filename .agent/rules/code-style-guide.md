---
trigger: always_on
---

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

**Project Structure:**
```
app/
├── common/          # Shared utilities (config, security, database)
├── features/        # Feature modules (auth, users, etc.)
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

## Coding Standards

- **Type hints required** for all functions
- **Async/await** for all I/O operations
- **Dependency injection** for sessions and auth
- **Pydantic validation** for all inputs
- **Argon2** for password hashing (no length limits)

## Development

```bash
make dev        # Start development server
make test       # Run tests
make test-cov   # Run tests with coverage
```

See [README.md](../README.md) for full documentation.
