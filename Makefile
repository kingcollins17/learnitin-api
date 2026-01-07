.PHONY: help install dev test test-cov clean lint format run migrate

# Use bash shell for all commands
SHELL := /bin/bash
PYTHON := venv/bin/python
PIP := venv/bin/pip
PYTEST := venv/bin/pytest

help:
	@echo "Available commands:"
	@echo "  make install     - Install dependencies"
	@echo "  make dev         - Start development server"
	@echo "  make test        - Run tests"
	@echo "  make test-cov    - Run tests with coverage"
	@echo "  make lint        - Run linting"
	@echo "  make format      - Format code"
	@echo "  make clean       - Clean cache files"

install:
	$(PIP) install -r requirements.txt

dev:
	@source venv/bin/activate && fastapi dev app/main.py

run:
	@source venv/bin/activate && uvicorn app.main:app --reload

test:
	@source venv/bin/activate && $(PYTEST) -v

test-cov:
	@source venv/bin/activate && $(PYTEST) --cov=app --cov-report=html --cov-report=term

test-auth:
	@source venv/bin/activate && $(PYTEST) tests/features/auth/ -v

test-users:
	@source venv/bin/activate && $(PYTEST) tests/features/users/ -v

lint:
	@source venv/bin/activate && ruff check app/ tests/

format:
	@source venv/bin/activate && black app/ tests/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete