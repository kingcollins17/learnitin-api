from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.common.config import settings
from app.common.database.session import init_db, close_db
from app.common.events.bus import event_bus
from app.features.auth.router import router as auth_router
from app.features.users.router import router as users_router
from app.features.courses.router import router as courses_router
from app.features.modules.router import router as modules_router
from app.features.lessons.router import router as lessons_router
from app.features.notifications.router import router as notifications_router
from app.features.notifications.websocket_manager import notification_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup: Initialize database and event bus
    await init_db()
    event_bus.start()

    # Initialize real-time notification manager subscription
    notification_manager.subscribe_to_bus()
    yield
    # Shutdown: Close database connections and stop event bus
    await event_bus.stop()
    await close_db()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="LearnItIn API - Educational platform backend",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,  # type: ignore
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers from feature modules
app.include_router(
    auth_router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["Authentication"]
)
app.include_router(
    users_router, prefix=f"{settings.API_V1_PREFIX}/users", tags=["Users"]
)
app.include_router(
    courses_router, prefix=f"{settings.API_V1_PREFIX}/courses", tags=["Courses"]
)
app.include_router(
    modules_router, prefix=f"{settings.API_V1_PREFIX}/modules", tags=["Modules"]
)
app.include_router(
    lessons_router, prefix=f"{settings.API_V1_PREFIX}/lessons", tags=["Lessons"]
)
app.include_router(
    notifications_router,
    prefix=f"{settings.API_V1_PREFIX}/notifications",
    tags=["Notifications"],
)


@app.get("/")
async def root():
    return {
        "message": "Welcome to LearnItIn API",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
