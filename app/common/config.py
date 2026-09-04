"""Application configuration settings."""

from pydantic import Field
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = Field(default="LearnItIn API")
    APP_VERSION: str = Field(default="1.0.0")
    ENVIRONMENT: str = Field(
        default="staging",
        description="Application environment: 'production', 'staging', or 'development'",
    )
    DEBUG: bool = Field(default=True)
    API_V1_PREFIX: str = Field(default="/api/v1")

    # Security
    SECRET_KEY: str = Field()
    ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=43200)

    # Database - MySQL Configuration
    DATABASE_URL: str = Field(default="")
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
    DB_ECHO: bool = Field(default=False)

    # OpenAI / LangChain
    OPENAI_API_KEY: str = Field(default="")

    # Gemini
    GEMINI_API_KEY: str = Field(default="")

    # Deepseek
    DEEPSEEK_API_KEY: str = Field(default="")

    # AI Provider
    DEFAULT_AI_PROVIDER: str = Field(default="deepseek")

    # Deepgram
    DEEPGRAM_API_KEY: str = Field(default="")

    # Audio Provider
    DEFAULT_AUDIO_PROVIDER: str = Field(default="deepgram")

    # Email
    EMAIL_FROM: str = Field(default="noreply@learnitin.online")
    RESEND_API_KEY: str = Field(default="")
    APP_LOGO: str = Field(
        default="https://drive.google.com/uc?export=view&id=1Fg6pBCL3bAG_r9NmP4WJKZ-1ae6N8iHa"
    )

    # Firebase
    FIREBASE_STORAGE_BUCKET: str = Field(default="")
    FIREBASE_CREDENTIALS_JSON: str = Field(default="")

    # Storage Provider Configuration
    STORAGE_PROVIDER: str = Field(
        default="firebase",
        description="Storage provider to use: 'firebase', 'r2', or 'gdrive'",
    )
    R2_ACCOUNT_ID: str = Field(default="")
    R2_ACCESS_KEY_ID: str = Field(default="")
    R2_SECRET_ACCESS_KEY: str = Field(default="")
    R2_BUCKET_NAME: str = Field(default="")
    R2_PUBLIC_DOMAIN: str = Field(default="")

    R2_JURISDICTION: str=Field(default='default')

    # Google Drive Storage Configuration
    GOOGLE_DRIVE_CREDENTIALS_JSON: str = Field(default="")
    GOOGLE_DRIVE_FOLDER_ID: str = Field(default="")

    # Google Play
    GOOGLE_PLAY_PACKAGE_NAME: str = Field(default="com.learnitin.learnitin")
    GOOGLE_PLAY_MOCK: bool = Field(default=False)

    # Google Auth
    GOOGLE_CLIENT_ID: str = Field(default="")

    # Credits
    NEW_USER_WELCOME_CREDITS: int = Field(default=100)
    STREAK_7_DAY_BONUS: int = Field(default=60)
    COURSE_GENERATION_COST: int = Field(default=10)

    # STORAGE AVAILABLE
    STORAGE_AVAILABLE: bool = Field(
        default=False, description="Whether the app storage service is back online"
    )
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:8000",
            "http://localhost:5173",  # Vite default
        ]
    )

    model_config = {
        "case_sensitive": True,
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",  # Ignore extra fields from .env file
    }


settings = Settings()
