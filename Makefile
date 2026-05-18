.PHONY: help install dev test test-cov test-auth test-users clean lint format run sync-env

# Automatically detect virtual environment directory (venv or env) using Make's native wildcard
ifneq ($(wildcard venv/),)
    VENV_DIR := venv
else
    VENV_DIR := env
endif

# Detect operating system
ifeq ($(OS),Windows_NT)
    VENV_BIN := $(VENV_DIR)\Scripts
    PYTHON := $(VENV_BIN)\python.exe
    PIP := $(VENV_BIN)\pip.exe
    PYTEST := $(VENV_BIN)\pytest.exe
    FASTAPI := $(VENV_BIN)\fastapi.exe
    UVICORN := $(VENV_BIN)\uvicorn.exe
    
    # Clean command for Windows PowerShell
    CLEAN_CMD := powershell -Command "Get-ChildItem -Recurse -Filter '__pycache__' | Remove-Item -Recurse -Force; Get-ChildItem -Recurse -Filter '*.pyc' | Remove-Item -Force; Get-ChildItem -Recurse -Filter '*.egg-info' | Remove-Item -Recurse -Force; Get-ChildItem -Recurse -Filter '.pytest_cache' | Remove-Item -Recurse -Force; Get-ChildItem -Recurse -Filter 'htmlcov' | Remove-Item -Recurse -Force; if (Test-Path .coverage) { Remove-Item .coverage -Force }"
else
    # Only force bash on non-Windows systems to avoid errors on Windows
    SHELL := /bin/bash
    
    VENV_BIN := $(VENV_DIR)/bin
    PYTHON := $(VENV_BIN)/python
    PIP := $(VENV_BIN)/pip
    PYTEST := $(VENV_BIN)/pytest
    FASTAPI := $(VENV_BIN)/fastapi
    UVICORN := $(VENV_BIN)/uvicorn
    
    # Clean command for macOS/Linux
    CLEAN_CMD := find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true; find . -type f -name "*.pyc" -delete; find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true; find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true; find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true; find . -type f -name ".coverage" -delete
endif

# Check if ruff exists inside the venv, otherwise fall back to system ruff
RUFF := $(wildcard $(VENV_BIN)/ruff*)
ifeq ($(RUFF),)
    RUFF := ruff
endif

# Check if black exists inside the venv, otherwise fall back to system black
BLACK := $(wildcard $(VENV_BIN)/black*)
ifeq ($(BLACK),)
    BLACK := black
endif

help:
	@echo ========================================================================
	@echo  LearnItIn API - Development Command Palette
	@echo ========================================================================
	@echo Available commands:
	@echo   make install     - Install dependencies from requirements.txt
	@echo   make dev         - Start FastAPI development server (auto-reload)
	@echo   make run         - Run Uvicorn server in production-like reload mode
	@echo   make test        - Run all tests using Pytest
	@echo   make test-cov    - Run tests with HTML and terminal coverage reports
	@echo   make test-auth   - Run authentication tests only
	@echo   make test-users  - Run user feature tests only
	@echo   make lint        - Perform linting check using Ruff
	@echo   make format      - Auto-format code using Black
	@echo   make sync-env    - Fetch and merge environment variables from Cloud Run
	@echo   make clean       - Clean pycache, coverage files, and build artifacts
	@echo ========================================================================
	@echo Detected virtual environment directory: $(VENV_DIR)

install:
	$(PIP) install -r requirements.txt

dev:
	$(FASTAPI) dev app/main.py

run:
	$(UVICORN) app.main:app --reload

test:
	$(PYTEST) -v

test-cov:
	$(PYTEST) --cov=app --cov-report=html --cov-report=term

test-auth:
	$(PYTEST) tests/features/auth/ -v

test-users:
	$(PYTEST) tests/features/users/ -v

lint:
	$(RUFF) check app/ tests/

format:
	$(BLACK) app/ tests/

clean:
	@echo Cleaning up temporary files and directories...
	@$(CLEAN_CMD)
	@echo Cleanup completed successfully!

sync-env:
	$(PYTHON) scripts/fetch_env_vars.py