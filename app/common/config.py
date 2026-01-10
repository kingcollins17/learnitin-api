"""Application configuration settings."""

from pydantic import Field
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = Field(default="LearnItIn API")
    APP_VERSION: str = Field(default="1.0.0")
    DEBUG: bool = Field(default=True)
    API_V1_PREFIX: str = Field(default="/api/v1")

    # Security
    SECRET_KEY: str = Field(default="your-secret-key-change-in-production")
    ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)

    # Database - MySQL Configuration
    DB_HOST: str = Field(default="localhost")
    DB_PORT: int = Field(default=3306)
    DB_USER: str = Field(default="root")
    DB_PASSWORD: str = Field(default="")
    DB_NAME: str = Field(default="learnitin_db")
    DB_ROOT_USER: str = Field(default="root")
    DB_ROOT_PASSWORD: str = Field(default="")

    # Database Connection Pool Settings
    DB_POOL_SIZE: int = Field(default=5)
    DB_MAX_OVERFLOW: int = Field(default=10)

    # OpenAI / LangChain
    OPENAI_API_KEY: str = Field(default="")

    # Gemini
    GEMINI_API_KEY: str = Field(default="")

    # Email
    EMAIL_FROM: str = Field(default="noreply@learnitin.com")
    RESEND_API_KEY: str = Field(default="")

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:8000",
            "http://localhost:5173",  # Vite default
        ]
    )

    @property
    def DATABASE_URL(self) -> str:
        """
        Construct async MySQL database URL.
        Format: mysql+asyncmy://user:password@host:port/database
        """
        return f"mysql+asyncmy://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    model_config = {
        "case_sensitive": True,
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",  # Ignore extra fields from .env file
    }


settings = Settings()
