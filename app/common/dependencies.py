"""Shared dependencies for services and repositories."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.database.session import get_async_session

# --- Auth & Users ---
from app.features.users.repository import UserRepository
from app.features.auth.otp_repository import OTPRepository
from app.features.users.service import UserService
from app.features.auth.otp_service import OTPService
from app.features.auth.service import AuthService

# --- Courses ---
from app.features.courses.repository import (
    CourseRepository,
    UserCourseRepository,
    CategoryRepository,
    SubCategoryRepository,
)
from app.features.modules.repository import ModuleRepository
from app.features.lessons.repository import LessonRepository
from app.features.courses.service import (
    CourseService,
    CategoryService,
    SubCategoryService,
)
from app.features.courses.generation_service import CourseGenerationService

# --- Subscriptions ---
from app.features.subscriptions.repository import SubscriptionRepository
from app.features.subscriptions.usage_repository import SubscriptionUsageRepository
from app.features.subscriptions.service import SubscriptionService
from app.features.subscriptions.usage_service import SubscriptionUsageService
from app.features.subscriptions.google_play_service import GooglePlayService


# ========== Auth & Users Dependencies ==========


def get_user_repository(
    session: AsyncSession = Depends(get_async_session),
) -> UserRepository:
    return UserRepository(session)


def get_user_service(
    repo: UserRepository = Depends(get_user_repository),
) -> UserService:
    return UserService(repo)


def get_otp_repository(
    session: AsyncSession = Depends(get_async_session),
) -> OTPRepository:
    return OTPRepository(session)


def get_otp_service(repo: OTPRepository = Depends(get_otp_repository)) -> OTPService:
    return OTPService(repo)


def get_auth_service(
    session: AsyncSession = Depends(get_async_session),
    user_service: UserService = Depends(get_user_service),
    otp_service: OTPService = Depends(get_otp_service),
) -> AuthService:
    return AuthService(session, user_service, otp_service)


# ========== Courses Dependencies ==========


def get_course_repository(
    session: AsyncSession = Depends(get_async_session),
) -> CourseRepository:
    return CourseRepository(session)


def get_module_repository(
    session: AsyncSession = Depends(get_async_session),
) -> ModuleRepository:
    return ModuleRepository(session)


def get_lesson_repository(
    session: AsyncSession = Depends(get_async_session),
) -> LessonRepository:
    return LessonRepository(session)


def get_user_course_repository(
    session: AsyncSession = Depends(get_async_session),
) -> UserCourseRepository:
    return UserCourseRepository(session)


def get_category_repository(
    session: AsyncSession = Depends(get_async_session),
) -> CategoryRepository:
    return CategoryRepository(session)


def get_subcategory_repository(
    session: AsyncSession = Depends(get_async_session),
) -> SubCategoryRepository:
    return SubCategoryRepository(session)


def get_course_generation_service() -> CourseGenerationService:
    return CourseGenerationService()


def get_course_service(
    session: AsyncSession = Depends(get_async_session),
    course_repo: CourseRepository = Depends(get_course_repository),
    module_repo: ModuleRepository = Depends(get_module_repository),
    lesson_repo: LessonRepository = Depends(get_lesson_repository),
    user_course_repo: UserCourseRepository = Depends(get_user_course_repository),
) -> CourseService:
    return CourseService(
        session, course_repo, module_repo, lesson_repo, user_course_repo
    )


def get_category_service(
    session: AsyncSession = Depends(get_async_session),
    category_repo: CategoryRepository = Depends(get_category_repository),
) -> CategoryService:
    return CategoryService(session, category_repo)


def get_subcategory_service(
    session: AsyncSession = Depends(get_async_session),
    subcategory_repo: SubCategoryRepository = Depends(get_subcategory_repository),
    category_repo: CategoryRepository = Depends(get_category_repository),
) -> SubCategoryService:
    return SubCategoryService(session, subcategory_repo, category_repo)


# ========== Subscriptions Dependencies ==========


def get_google_play_service() -> GooglePlayService:
    return GooglePlayService()


def get_subscription_repository(
    session: AsyncSession = Depends(get_async_session),
) -> SubscriptionRepository:
    return SubscriptionRepository(session)


def get_subscription_usage_repository(
    session: AsyncSession = Depends(get_async_session),
) -> SubscriptionUsageRepository:
    return SubscriptionUsageRepository(session)


def get_subscription_service(
    session: AsyncSession = Depends(get_async_session),
    repo: SubscriptionRepository = Depends(get_subscription_repository),
    usage_repo: SubscriptionUsageRepository = Depends(
        get_subscription_usage_repository
    ),
    google_play: GooglePlayService = Depends(get_google_play_service),
) -> SubscriptionService:
    return SubscriptionService(session, repo, usage_repo, google_play)


def get_subscription_usage_service(
    session: AsyncSession = Depends(get_async_session),
    usage_repo: SubscriptionUsageRepository = Depends(
        get_subscription_usage_repository
    ),
    sub_service: SubscriptionService = Depends(get_subscription_service),
) -> SubscriptionUsageService:
    return SubscriptionUsageService(session, usage_repo, sub_service)
