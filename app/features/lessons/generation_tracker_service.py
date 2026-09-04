"""Service for tracking lesson content and audio generation state in database."""

import json
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, col, desc

from app.features.lessons.models import (
    LessonGenerationState,
    GenerationType,
    GenerationStatus,
)


class LessonGenerationTrackerService:
    """Service for interacting with database generation state records."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def start_tracking(
        self,
        user_id: int,
        generation_type: GenerationType,
        lesson_id: Optional[int] = None,
        provider: Optional[str] = None,
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, LessonGenerationState]:
        """
        Mark generation process as started for a user/lesson.
        Returns (True, state) if started, or (False, existing_state) if already in progress.
        """
        # Check if already in progress for this lesson and generation_type
        if lesson_id is not None:
            existing = await self.get_active_generation_state(
                generation_type=generation_type,
                lesson_id=lesson_id,
            )
            if existing:
                return False, existing

        metadata_json = json.dumps(metadata) if metadata else None
        new_state = LessonGenerationState(
            user_id=user_id,
            lesson_id=lesson_id,
            generation_type=generation_type,
            status=GenerationStatus.IN_PROGRESS,
            provider=provider,
            task_id=task_id,
            metadata_json=metadata_json,
            started_at=datetime.now(timezone.utc),
        )

        self.session.add(new_state)
        await self.session.flush()
        await self.session.refresh(new_state)
        return True, new_state

    async def complete_tracking(
        self,
        generation_type: GenerationType,
        lesson_id: Optional[int] = None,
        tracker_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[LessonGenerationState]:
        """
        Mark active generation process as COMPLETED.
        """
        state = await self._get_target_state(
            tracker_id=tracker_id,
            lesson_id=lesson_id,
            generation_type=generation_type,
        )
        if not state:
            return None

        state.status = GenerationStatus.COMPLETED
        state.completed_at = datetime.now(timezone.utc)
        state.updated_at = datetime.now(timezone.utc)
        if metadata:
            state.metadata_json = json.dumps(metadata)

        self.session.add(state)
        await self.session.flush()
        await self.session.refresh(state)
        return state

    async def fail_tracking(
        self,
        generation_type: GenerationType,
        error_message: str,
        lesson_id: Optional[int] = None,
        tracker_id: Optional[int] = None,
    ) -> Optional[LessonGenerationState]:
        """
        Mark active generation process as FAILED with error message.
        """
        state = await self._get_target_state(
            tracker_id=tracker_id,
            lesson_id=lesson_id,
            generation_type=generation_type,
        )
        if not state:
            return None

        state.status = GenerationStatus.FAILED
        state.error_message = error_message
        state.completed_at = datetime.now(timezone.utc)
        state.updated_at = datetime.now(timezone.utc)

        self.session.add(state)
        await self.session.flush()
        await self.session.refresh(state)
        return state

    async def is_in_progress(
        self,
        generation_type: GenerationType,
        lesson_id: Optional[int] = None,
    ) -> bool:
        """
        Check if generation is currently in progress.
        """
        state = await self.get_active_generation_state(
            generation_type=generation_type,
            lesson_id=lesson_id,
        )
        return state is not None

    async def get_active_generation_state(
        self,
        generation_type: GenerationType,
        lesson_id: Optional[int] = None,
    ) -> Optional[LessonGenerationState]:
        """
        Get current IN_PROGRESS or PENDING generation state for lesson/generation_type.
        """
        query = (
            select(LessonGenerationState)
            .where(col(LessonGenerationState.generation_type) == generation_type)
            .where(
                col(LessonGenerationState.status).in_(
                    [GenerationStatus.IN_PROGRESS, GenerationStatus.PENDING]
                )
            )
        )
        if lesson_id is not None:
            query = query.where(LessonGenerationState.lesson_id == lesson_id)

        query = query.order_by(desc(LessonGenerationState.id)).limit(1)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_latest_generation_state(
        self,
        generation_type: GenerationType,
        lesson_id: Optional[int] = None,
    ) -> Optional[LessonGenerationState]:
        """
        Get latest generation state record regardless of status.
        """
        query = select(LessonGenerationState).where(
            col(LessonGenerationState.generation_type) == generation_type
        )
        if lesson_id is not None:
            query = query.where(LessonGenerationState.lesson_id == lesson_id)

        query = query.order_by(desc(LessonGenerationState.id)).limit(1)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_tracked_lessons(
        self,
        generation_type: Optional[GenerationType] = None,
    ) -> Dict[int, int]:
        """
        Get map of active lesson_id -> user_id currently undergoing generation.
        """
        query = select(LessonGenerationState).where(
            col(LessonGenerationState.status).in_(
                [GenerationStatus.IN_PROGRESS, GenerationStatus.PENDING]
            )
        )
        if generation_type is not None:
            query = query.where(col(LessonGenerationState.generation_type) == generation_type)

        result = await self.session.execute(query)
        active_states = result.scalars().all()
        return {
            state.lesson_id: state.user_id
            for state in active_states
            if state.lesson_id is not None
        }

    async def get_generation_states_by_lesson_id(
        self,
        lesson_id: int,
        generation_type: Optional[GenerationType] = None,
        statuses: Optional[list[str]] = None,
    ) -> list[LessonGenerationState]:
        """
        Fetch all generation states for a given lesson_id, optionally filtered by generation_type and statuses.
        """
        query = select(LessonGenerationState).where(LessonGenerationState.lesson_id == lesson_id)
        if generation_type is not None:
            query = query.where(col(LessonGenerationState.generation_type) == generation_type)
        if statuses:
            query = query.where(col(LessonGenerationState.status).in_(statuses))

        query = query.order_by(desc(LessonGenerationState.id))
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def _get_target_state(
        self,
        tracker_id: Optional[int],
        lesson_id: Optional[int],
        generation_type: GenerationType,
    ) -> Optional[LessonGenerationState]:
        if tracker_id is not None:
            result = await self.session.execute(
                select(LessonGenerationState).where(LessonGenerationState.id == tracker_id)
            )
            return result.scalar_one_or_none()
        elif lesson_id is not None:
            return await self.get_active_generation_state(
                generation_type=generation_type,
                lesson_id=lesson_id,
            )
        return None
