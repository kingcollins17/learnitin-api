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
from app.features.quiz.router import router as quiz_router
from app.features.subscriptions.router import router as subscriptions_router
from app.features.notifications.handlers import handle_in_app_push_for_fcm
from app.common.events import NotificationInAppPushEvent


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup: Initialize database
    await init_db()

    # Register notification event handlers
    event_bus.on(
        NotificationInAppPushEvent, handle_in_app_push_for_fcm
    )  # ty:ignore[no-matching-overload]

    # Register subscription event handlers for Google Play webhooks
    from app.features.subscriptions.events import (
        SubscriptionPurchasedEvent,
        SubscriptionRenewedEvent,
        SubscriptionCanceledEvent,
        SubscriptionExpiredEvent,
        SubscriptionPausedEvent,
        SubscriptionResumedEvent,
        SubscriptionRevokedEvent,
        SubscriptionGracePeriodEvent,
        SubscriptionRecoveredEvent,
    )
    from app.features.subscriptions.handlers import (
        handle_subscription_purchased,
        handle_subscription_renewed,
        handle_subscription_canceled,
        handle_subscription_expired,
        handle_subscription_paused,
        handle_subscription_resumed,
        handle_subscription_revoked,
        handle_subscription_grace_period,
        handle_subscription_recovered,
    )

    event_bus.on(SubscriptionPurchasedEvent, handle_subscription_purchased)  # type: ignore
    event_bus.on(SubscriptionRenewedEvent, handle_subscription_renewed)  # type: ignore
    event_bus.on(SubscriptionCanceledEvent, handle_subscription_canceled)  # type: ignore
    event_bus.on(SubscriptionExpiredEvent, handle_subscription_expired)  # type: ignore
    event_bus.on(SubscriptionPausedEvent, handle_subscription_paused)  # type: ignore
    event_bus.on(SubscriptionResumedEvent, handle_subscription_resumed)  # type: ignore
    event_bus.on(SubscriptionRevokedEvent, handle_subscription_revoked)  # type: ignore
    event_bus.on(SubscriptionGracePeriodEvent, handle_subscription_grace_period)  # type: ignore
    event_bus.on(SubscriptionRecoveredEvent, handle_subscription_recovered)  # type: ignore

    yield
    # Shutdown: Close database connections and stop event bus
    await event_bus.stop(clear=True)
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
app.include_router(
    quiz_router,
    prefix=f"{settings.API_V1_PREFIX}/quiz",
    tags=["Quizzes"],
)
app.include_router(
    subscriptions_router,
    prefix=f"{settings.API_V1_PREFIX}",
    tags=["Subscriptions"],
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
