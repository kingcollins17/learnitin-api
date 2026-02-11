"""Service for database maintenance and cleanup tasks."""

import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.lessons.repository import LessonAudioRepository
from app.features.courses.repository import CourseRepository
from app.services.storage_service import FirebaseStorageService
from app.common.service import Commitable

logger = logging.getLogger(__name__)


class DBMaintenanceService(Commitable):
    """Service for cross-feature database maintenance operations."""

    def __init__(
        self,
        audio_repo: LessonAudioRepository,
        course_repo: CourseRepository,
        storage_service: FirebaseStorageService,
    ):

        self.audio_repo = audio_repo
        self.course_repo = course_repo
        self.storage_service = storage_service

    async def commit_all(self) -> None:
        """Commit all active sessions in the service's repositories."""
        await self.audio_repo.session.commit()
        await self.course_repo.session.commit()

    async def cleanup_orphaned_audios(self) -> dict:
        """
        Identify and delete LessonAudio records that are no longer linked to a lesson.

        Process:
        1. Fetch all LessonAudio records where lesson_id is NULL.
        2. Delete the files from Firebase Storage using their audio_url.
        3. Delete the records from the database.
        """
        logger.info("Starting orphaned audios cleanup...")
        orphaned_audios = await self.audio_repo.get_orphaned_audios()

        if not orphaned_audios:
            logger.info("No orphaned audios found.")
            return {"deleted_count": 0, "storage_deleted": 0}

        logger.info(f"Found {len(orphaned_audios)} orphaned audios.")
        deleted_from_storage = 0
        deleted_from_db = 0

        for audio in orphaned_audios:
            if audio.audio_url:
                if self.storage_service.delete_file(audio.audio_url):
                    deleted_from_storage += 1
                else:
                    logger.warning(
                        f"Failed to delete audio file from storage: {audio.audio_url}"
                    )

            await self.audio_repo.delete(audio)
            deleted_from_db += 1

        await self.audio_repo.session.commit()

        results = {
            "orphans_found": len(orphaned_audios),
            "storage_deleted": deleted_from_storage,
            "db_deleted": deleted_from_db,
        }
        logger.info(f"Audio cleanup completed: {results}")
        return results

    async def cleanup_orphaned_courses(self) -> dict:
        """
        Identify and delete Course records that have no creator and are not public.

        Process:
        1. Fetch courses where user_id is NULL and is_public is FALSE.
        2. Delete the course image from Firebase Storage.
        3. Delete the record from the database.
        """
        logger.info("Starting orphaned courses cleanup...")
        orphaned_courses = await self.course_repo.get_orphaned_courses()

        if not orphaned_courses:
            logger.info("No orphaned courses found.")
            return {"deleted_count": 0, "storage_deleted": 0}

        logger.info(f"Found {len(orphaned_courses)} orphaned courses.")
        deleted_from_storage = 0
        deleted_from_db = 0

        for course in orphaned_courses:
            if course.image_url:
                if self.storage_service.delete_file(course.image_url):
                    deleted_from_storage += 1
                else:
                    logger.warning(
                        f"Failed to delete course image from storage: {course.image_url}"
                    )

            await self.course_repo.delete(course)
            deleted_from_db += 1

        await self.course_repo.session.commit()

        results = {
            "orphans_found": len(orphaned_courses),
            "storage_deleted": deleted_from_storage,
            "db_deleted": deleted_from_db,
        }
        logger.info(f"Course cleanup completed: {results}")
        return results

    async def run_all_maintenance(self) -> dict:
        """Run all identified maintenance tasks."""
        logger.info("Running all database maintenance tasks...")
        results = {}

        try:
            results["audios"] = await self.cleanup_orphaned_audios()
        except Exception as e:
            logger.error(f"Audio cleanup error: {e}", exc_info=True)
            results["audios"] = {"error": str(e)}

        try:
            results["courses"] = await self.cleanup_orphaned_courses()
        except Exception as e:
            logger.error(f"Course cleanup error: {e}", exc_info=True)
            results["courses"] = {"error": str(e)}

        logger.info("Database maintenance tasks completed.")
        return results
