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
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=43200)

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
    EMAIL_FROM: str = Field(default="noreply@learnitin.online")
    RESEND_API_KEY: str = Field(default="")
    APP_LOGO: str = Field(
        default="https://drive.google.com/uc?export=view&id=1Fg6pBCL3bAG_r9NmP4WJKZ-1ae6N8iHa"
    )

    # Firebase
    FIREBASE_STORAGE_BUCKET: str = Field(default="")
    FIREBASE_CREDENTIALS_JSON: str = Field(default="")

    # Google Play
    GOOGLE_PLAY_PACKAGE_NAME: str = Field(default="com.learnitin.learnitin")
    GOOGLE_PLAY_MOCK: bool = Field(default=False)

    # Google Auth
    GOOGLE_CLIENT_ID: str = Field(default="")

    # Free Plan Limits (per month)
    FREE_PLAN_LEARNING_JOURNEYS_LIMIT: int = Field(default=2)
    FREE_PLAN_LESSONS_LIMIT: int = Field(default=10)
    FREE_PLAN_AUDIO_LESSONS_LIMIT: int = Field(default=5)

    # Subscription Grace Period (days after expiry before demotion to free)
    SUBSCRIPTION_GRACE_PERIOD_DAYS: int = Field(default=3)

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
