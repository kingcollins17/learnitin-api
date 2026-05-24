"""Common dependencies for FastAPI endpoints."""

import traceback
from typing import Optional, Literal
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.common.security import decode_access_token
from app.common.database.session import get_async_session
from app.features.users.models import User
from app.features.credits.service import CreditService, InsufficientCreditsError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_async_session),
) -> User:
    """Get the current authenticated user."""
    try:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        print(f"token is {token}")
        payload = decode_access_token(token)
        print(f"payload is {payload}")
        if payload is None:
            raise credentials_exception

        user_id: Optional[str] = payload.get("sub")
        print(f"user_id is {user_id}")
        if user_id is None:
            raise credentials_exception

        # Use SQLModel async query
        result = await session.execute(select(User).where(User.id == int(user_id)))
        user = result.scalar_one_or_none()

        if user is None:
            raise credentials_exception

        return user
    except Exception as e:
        traceback.print_exc()
        raise e


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get the current active user.

    This dependency requires that the user's account is verified (is_active=True).
    Use this for endpoints that should only be accessible to verified users.

    For endpoints that should be accessible to all authenticated users (including
    unverified ones), use `get_current_user` instead.

    Raises:
        HTTPException: 400 if the user's account is not active
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_current_user_optional(
    token: Optional[str] = Depends(
        OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)
    ),
    session: AsyncSession = Depends(get_async_session),
) -> Optional[User]:
    """Get the current authenticated user if token is provided, otherwise return None."""
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        if payload is None:
            return None

        user_id: Optional[str] = payload.get("sub")
        if user_id is None:
            return None

        result = await session.execute(select(User).where(User.id == int(user_id)))
        return result.scalar_one_or_none()
    except Exception:
        return None


async def get_current_active_user_optional(
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> Optional[User]:
    """Get the current active user if authenticated, otherwise return None."""
    if current_user and not current_user.is_active:
        return None
    return current_user


class HasSufficientCredits:
    """Dependency to check if the user has sufficient credits for an action.

    Usage in router endpoints:
        @router.post("/generate", dependencies=[Depends(HasSufficientCredits(50))])
        async def my_endpoint(...):
            ...
    """

    def __init__(self, credit_requirement: int):
        self.credit_requirement = credit_requirement

    async def __call__(
        self,
        current_user: User = Depends(get_current_active_user),
        session: AsyncSession = Depends(get_async_session),
    ) -> User:
        from app.features.credits.repository import CreditRepository
        from app.features.credits.service import CreditService

        credit_repo = CreditRepository(session)
        credit_service = CreditService(credit_repo)
        assert current_user.id is not None, "Current User ID cannot be None"
        balance = await credit_service.get_balance(current_user.id)
        if balance < self.credit_requirement:
            raise InsufficientCreditsError(balance=balance, required=self.credit_requirement)
        return current_user


class HasSufficientLessonCredits:
    """Dependency to check if the user has sufficient credits to generate lesson content, audio, or quiz.

    It fetches the lesson by the path parameter `lesson_id` and checks the corresponding action cost.

    Usage in router endpoints:
        @router.post("/lessons/{lesson_id}/audio", dependencies=[Depends(HasSufficientLessonCredits("audio"))])
        async def generate_lesson_audio(lesson_id: int, ...):
            ...
    """

    def __init__(self, action: Literal["content", "audio", "quiz"]):
        self.action = action

    async def __call__(
        self,
        lesson_id: int,  # Captured directly from route path parameters
        current_user: User = Depends(get_current_active_user),
        session: AsyncSession = Depends(get_async_session),
    ) -> User:
        from app.features.lessons.repository import LessonRepository
        from app.features.credits.repository import CreditRepository
        from app.features.credits.service import CreditService

        # 1. Fetch lesson to check its configured cost
        lesson_repo = LessonRepository(session)
        lesson = await lesson_repo.get_by_id(lesson_id)
        if not lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lesson not found",
            )

        # 2. Determine credit requirement
        if self.action == "content":
            credit_requirement = lesson.credit_cost
        elif self.action == "audio":
            credit_requirement = lesson.audio_credit_cost
        elif self.action == "quiz":
            credit_requirement = lesson.quiz_credit_cost
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid credit action specified",
            )

        # 3. Check user credits balance
        credit_repo = CreditRepository(session)
        credit_service = CreditService(credit_repo)

        assert current_user.id is not None
        balance = await credit_service.get_balance(current_user.id)
        if balance < credit_requirement:
            raise InsufficientCreditsError(balance=balance, required=credit_requirement)

        return current_user
