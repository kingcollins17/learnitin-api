"""Shared dependencies for services and repositories."""

from app.services.audio_generation_service import AudioGenerationService
from app.services.audio_conversion_service import AudioConversionService
from app.services.storage_service import FirebaseStorageService
from app.services.email_service import EmailService
from app.services.image_generation_service import ImageGenerationService
from app.services.fcm_service import FirebaseFCMService
from app.common.config import Settings, settings

from app.services.maintenance_service import DBMaintenanceService
from app.services.langchain_service import LangChainService
from fastapi import Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.database.session import get_async_session

# --- Auth & Users ---
from app.features.users.repository import UserRepository
from app.features.auth.otp_repository import OTPRepository
from app.features.users.service import UserService
from app.features.auth.otp_service import OTPService
from app.features.auth.service import AuthService
from app.features.reviews.repository import ReviewRepository
from app.features.reviews.service import ReviewService
from app.features.quiz.repository import QuizRepository, QuestionRepository

from app.features.quiz.service import QuizService

from app.features.courses.service import (
    CourseService,
    CategoryService,
    SubCategoryService,
)
from app.features.courses.generation_service import CourseGenerationService
from app.features.lessons.generation_service import LessonGenerationService
from app.features.quiz.generation_service import QuizGenerationService
from app.features.lessons.lecture_service import (
    LectureConversionService,
    LectureBreakdownService,
)

# --- Courses ---
from app.features.courses.repository import (
    CourseRepository,
    UserCourseRepository,
    CategoryRepository,
    SubCategoryRepository,
)

# --- Modules ---
from app.features.modules.repository import ModuleRepository, UserModuleRepository
from app.features.modules.service import ModuleService, UserModuleService

# --- Lessons ---
from app.features.lessons.repository import (
    LessonRepository,
    UserLessonRepository,
    LessonAudioRepository,
)
from app.features.lessons.service import LessonService, UserLessonService

# --- Notifications ---
from app.features.notifications.repository import NotificationRepository
from app.features.notifications.service import NotificationService

# --- Subscriptions ---
from app.features.subscriptions.repository import SubscriptionRepository
from app.features.subscriptions.usage_repository import SubscriptionUsageRepository
from app.features.subscriptions.service import SubscriptionService
from app.features.subscriptions.usage_service import SubscriptionUsageService
from app.features.subscriptions.google_play_service import GooglePlayService


# ========== Repositories ==========


def get_user_repository(
    session: AsyncSession = Depends(get_async_session),
) -> UserRepository:
    return UserRepository(session)


def get_otp_repository(
    session: AsyncSession = Depends(get_async_session),
) -> OTPRepository:
    return OTPRepository(session)


def get_review_repository(
    session: AsyncSession = Depends(get_async_session),
) -> ReviewRepository:
    """Dependency for review repository."""
    return ReviewRepository(session)


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


def get_lesson_audio_repo(
    session: AsyncSession = Depends(get_async_session),
) -> LessonAudioRepository:
    return LessonAudioRepository(session=session)


def get_user_lesson_repository(
    session: AsyncSession = Depends(get_async_session),
) -> UserLessonRepository:
    return UserLessonRepository(session)


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


def get_user_module_repository(
    session: AsyncSession = Depends(get_async_session),
) -> UserModuleRepository:
    return UserModuleRepository(session)


def get_notification_repository(
    session: AsyncSession = Depends(get_async_session),
) -> NotificationRepository:
    return NotificationRepository(session)


def get_subscription_repository(
    session: AsyncSession = Depends(get_async_session),
) -> SubscriptionRepository:
    return SubscriptionRepository(session)


def get_subscription_usage_repository(
    session: AsyncSession = Depends(get_async_session),
) -> SubscriptionUsageRepository:
    return SubscriptionUsageRepository(session)


def get_quiz_repository(
    session: AsyncSession = Depends(get_async_session),
) -> QuizRepository:
    return QuizRepository(session)


def get_question_repository(
    session: AsyncSession = Depends(get_async_session),
) -> QuestionRepository:
    return QuestionRepository(session)


# ========== Util Services ==========

# Singleton instances
_settings = settings
_langchain_service = LangChainService(settings=_settings, backend="gemini")
_lecture_breakdown_service = LectureBreakdownService(_langchain_service)


def get_settings() -> Settings:
    return _settings


def get_langchain_service() -> LangChainService:
    return _langchain_service


def get_course_generation_service(
    ai_service: LangChainService = Depends(get_langchain_service),
) -> CourseGenerationService:
    return CourseGenerationService(ai_service)


def get_lesson_generation_service(
    ai_service: LangChainService = Depends(get_langchain_service),
) -> LessonGenerationService:
    return LessonGenerationService(ai_service)


def get_quiz_generation_service(
    ai_service: LangChainService = Depends(get_langchain_service),
) -> QuizGenerationService:
    return QuizGenerationService(ai_service)


def get_lecture_breakdown_service() -> LectureBreakdownService:
    return _lecture_breakdown_service


# MARK: Lecture Conversion
def get_lecture_conversion_service(
    ai_service: LangChainService = Depends(get_langchain_service),
    breakdown_service: LectureBreakdownService = Depends(get_lecture_breakdown_service),
) -> LectureConversionService:
    return LectureConversionService(ai_service, breakdown_service)


def get_google_play_service() -> GooglePlayService:
    return GooglePlayService()


_firebase_storage_service = FirebaseStorageService(_settings)


def get_firebase_storage_service() -> FirebaseStorageService:
    return _firebase_storage_service


_audio_conversion_service = AudioConversionService()
_audio_generation_service = AudioGenerationService(_audio_conversion_service, _settings)
_firebase_fcm_service = FirebaseFCMService(_settings)


def get_audio_generation_service() -> AudioGenerationService:
    return _audio_generation_service


def get_audio_conversion_service() -> AudioConversionService:
    return _audio_conversion_service


def get_fcm_service() -> FirebaseFCMService:
    return _firebase_fcm_service


# ========== Normal Services ==========


def get_user_service(
    repo: UserRepository = Depends(get_user_repository),
) -> UserService:
    return UserService(repo)


_email_service = EmailService(_settings)


def get_email_service() -> EmailService:
    return _email_service


def get_otp_service(
    repository: OTPRepository = Depends(get_otp_repository),
    email_service: EmailService = Depends(get_email_service),
) -> OTPService:
    return OTPService(repository, email_service)


def get_auth_service(
    user_service: UserService = Depends(get_user_service),
    otp_service: OTPService = Depends(get_otp_service),
) -> AuthService:
    return AuthService(user_service, otp_service)


def get_review_service(
    review_repo: ReviewRepository = Depends(get_review_repository),
    course_repo: CourseRepository = Depends(get_course_repository),
) -> ReviewService:
    """Dependency for review service."""
    return ReviewService(review_repo, course_repo)


def get_category_service(
    category_repo: CategoryRepository = Depends(get_category_repository),
) -> CategoryService:
    return CategoryService(category_repo)


def get_subcategory_service(
    subcategory_repo: SubCategoryRepository = Depends(get_subcategory_repository),
    category_repo: CategoryRepository = Depends(get_category_repository),
) -> SubCategoryService:
    return SubCategoryService(subcategory_repo, category_repo)


_image_generation_service = ImageGenerationService(_settings)


def get_image_generation_service() -> ImageGenerationService:
    return _image_generation_service


def get_course_service(
    course_repo: CourseRepository = Depends(get_course_repository),
    module_repo: ModuleRepository = Depends(get_module_repository),
    lesson_repo: LessonRepository = Depends(get_lesson_repository),
    user_course_repo: UserCourseRepository = Depends(get_user_course_repository),
    review_repo: ReviewRepository = Depends(get_review_repository),
    storage_service: FirebaseStorageService = Depends(get_firebase_storage_service),
    image_gen_service: ImageGenerationService = Depends(get_image_generation_service),
) -> CourseService:
    return CourseService(
        course_repo,
        module_repo,
        lesson_repo,
        user_course_repo,
        review_repo,
        storage_service,
        image_gen_service,
    )


def get_module_service(
    module_repo: ModuleRepository = Depends(get_module_repository),
) -> ModuleService:
    return ModuleService(module_repo)


def get_user_module_service(
    user_module_repo: UserModuleRepository = Depends(get_user_module_repository),
    module_repo: ModuleRepository = Depends(get_module_repository),
    user_course_repo: UserCourseRepository = Depends(get_user_course_repository),
    lesson_repo: LessonRepository = Depends(get_lesson_repository),
    user_lesson_repo: UserLessonRepository = Depends(get_user_lesson_repository),
) -> UserModuleService:
    return UserModuleService(
        user_module_repository=user_module_repo,
        module_repository=module_repo,
        user_course_repository=user_course_repo,
        lesson_repository=lesson_repo,
        user_lesson_repository=user_lesson_repo,
    )


def get_lesson_service(
    lesson_repo: LessonRepository = Depends(get_lesson_repository),
    audio_repo: LessonAudioRepository = Depends(get_lesson_audio_repo),
    user_lesson_repo: UserLessonRepository = Depends(get_user_lesson_repository),
    course_repo: CourseRepository = Depends(get_course_repository),
    module_repo: ModuleRepository = Depends(get_module_repository),
    generation_service: LessonGenerationService = Depends(
        get_lesson_generation_service
    ),
    lecture_service: LectureConversionService = Depends(get_lecture_conversion_service),
    storage_service: FirebaseStorageService = Depends(get_firebase_storage_service),
    audio_gen_service: AudioGenerationService = Depends(get_audio_generation_service),
    audio_conversion_service: AudioConversionService = Depends(
        get_audio_conversion_service
    ),
) -> LessonService:
    return LessonService(
        lesson_repository=lesson_repo,
        lesson_audio_repository=audio_repo,
        user_lesson_repository=user_lesson_repo,
        course_repository=course_repo,
        module_repository=module_repo,
        generation_service=generation_service,
        lecture_service=lecture_service,
        audio_gen_service=audio_gen_service,
        storage_service=storage_service,
        audio_conversion_service=audio_conversion_service,
    )


def get_user_lesson_service(
    user_lesson_repo: UserLessonRepository = Depends(get_user_lesson_repository),
    lesson_repo: LessonRepository = Depends(get_lesson_repository),
    user_course_repo: UserCourseRepository = Depends(get_user_course_repository),
    user_module_repo: UserModuleRepository = Depends(get_user_module_repository),
    user_module_service: UserModuleService = Depends(get_user_module_service),
) -> UserLessonService:
    return UserLessonService(
        user_lesson_repository=user_lesson_repo,
        lesson_repository=lesson_repo,
        user_course_repository=user_course_repo,
        user_module_repository=user_module_repo,
        user_module_service=user_module_service,
    )


def get_notification_service(
    notification_repo: NotificationRepository = Depends(get_notification_repository),
) -> NotificationService:
    return NotificationService(notification_repo)


def get_subscription_service(
    repo: SubscriptionRepository = Depends(get_subscription_repository),
    usage_repo: SubscriptionUsageRepository = Depends(
        get_subscription_usage_repository
    ),
    google_play: GooglePlayService = Depends(get_google_play_service),
) -> SubscriptionService:
    return SubscriptionService(
        subscription_repository=repo,
        usage_repository=usage_repo,
        google_play=google_play,
    )


def get_subscription_usage_service(
    usage_repo: SubscriptionUsageRepository = Depends(
        get_subscription_usage_repository
    ),
    sub_service: SubscriptionService = Depends(get_subscription_service),
) -> SubscriptionUsageService:
    return SubscriptionUsageService(usage_repo, sub_service)


def get_db_maintenance_service(
    storage_service: FirebaseStorageService = Depends(get_firebase_storage_service),
    audio_repo: LessonAudioRepository = Depends(get_lesson_audio_repo),
    course_repo: CourseRepository = Depends(get_course_repository),
) -> DBMaintenanceService:
    return DBMaintenanceService(
        course_repo=course_repo,
        audio_repo=audio_repo,
        storage_service=storage_service,
    )


def get_quiz_service(
    quiz_repo: QuizRepository = Depends(get_quiz_repository),
    question_repo: QuestionRepository = Depends(get_question_repository),
    generation_service: QuizGenerationService = Depends(get_quiz_generation_service),
) -> QuizService:
    return QuizService(quiz_repo, question_repo, generation_service)


# ============= Action Dependencies ============
def run_db_maintenance_in_bg(
    bg: BackgroundTasks,
    maintenance_service: DBMaintenanceService = Depends(get_db_maintenance_service),
):
    bg.add_task(maintenance_service.run_all_maintenance)
