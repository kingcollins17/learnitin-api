from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.common.config import settings
from app.common.database.session import init_db, close_db
from app.features.auth.router import router as auth_router
from app.features.users.router import router as users_router
from app.features.courses.router import router as courses_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup: Initialize database
    await init_db()
    yield
    # Shutdown: Close database connections
    await close_db()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="LearnItIn API - Educational platform backend",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware, #type: ignore
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers from feature modules
app.include_router(auth_router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["Authentication"])
app.include_router(users_router, prefix=f"{settings.API_V1_PREFIX}/users", tags=["Users"])
app.include_router(courses_router, prefix=f"{settings.API_V1_PREFIX}/courses", tags=["Courses"])


@app.get("/")
async def root():
    return {
        "message": "Welcome to LearnItIn API",
        "version": settings.APP_VERSION,
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}

