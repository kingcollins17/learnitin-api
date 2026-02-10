"""Review service for business logic."""

from typing import Optional, List
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.reviews.models import Review
from app.features.reviews.schemas import ReviewCreate, ReviewUpdate, ReviewResponse
from app.features.reviews.repository import ReviewRepository, get_cached_summary
from app.features.courses.repository import CourseRepository
from datetime import datetime, timezone


class ReviewService:
    """Service for review business logic."""

    def __init__(
        self,
        session: AsyncSession,
        review_repo: ReviewRepository,
        course_repo: CourseRepository,
    ):
        """
        Initialize the ReviewService.

        Args:
            session: The asynchronous database session.
            review_repo: The repository for review data operations.
            course_repo: The repository for course data operations.
        """
        self.session = session
        self.review_repo = review_repo
        self.course_repo = course_repo

    async def create_review(
        self, user_id: int, review_in: ReviewCreate
    ) -> ReviewResponse:
        """
        Create a new review for a course.

        Validates that:
        1. The target course exists.
        2. The user has not already reviewed this specific course.

        Args:
            user_id: ID of the user creating the review.
            review_in: The review data (rating, comment, course_id).

        Returns:
            The newly created Review object.

        Raises:
            HTTPException: 404 if the course is not found.
            HTTPException: 400 if the user has already reviewed the course.
        """
        if not review_in.course_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="course_id is required",
            )
        # Check if course exists
        course = await self.course_repo.get_by_id(review_in.course_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Course with ID {review_in.course_id} not found",
            )

        # Check if user already reviewed this course
        existing_review = await self.review_repo.get(
            user_id=user_id, course_id=review_in.course_id
        )
        if existing_review:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have already reviewed this course",
            )

        review = Review(
            user_id=user_id,
            course_id=review_in.course_id,
            rating=review_in.rating,
            comment=review_in.comment,
        )
        created_review = await self.review_repo.create(review)
        get_cached_summary.cache_invalidate(review_in.course_id, self.review_repo)
        return ReviewResponse.model_validate(created_review)

    async def get_review(self, review_id: int) -> ReviewResponse:
        """
        Retrieve a single review by its ID.

        Args:
            review_id: The unique identifier of the review.

        Returns:
            Review: The found review object.

        Raises:
            HTTPException: 404 if the review does not exist.
        """
        review = await self.review_repo.get(review_id=review_id)
        if not review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Review not found"
            )
        return ReviewResponse.model_validate(review)

    async def get_course_reviews(
        self, course_id: int, skip: int = 0, limit: int = 100
    ) -> List[ReviewResponse]:
        """
        Get a paginated list of reviews for a specific course.

        Args:
            course_id: The ID of the course.
            skip: Number of records to skip (offset).
            limit: Maximum number of records to return.

        Returns:
            List[Review]: List of reviews associated with the course.
        """
        reviews = await self.review_repo.get_all(
            course_id=course_id, skip=skip, limit=limit
        )
        return [ReviewResponse.model_validate(r) for r in reviews]

    async def get_user_reviews(
        self, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[ReviewResponse]:
        """
        Get a paginated list of reviews written by a specific user.

        Args:
            user_id: The ID of the user.
            skip: Number of records to skip (offset).
            limit: Maximum number of records to return.

        Returns:
            List[Review]: List of reviews written by the user.
        """
        reviews = await self.review_repo.get_all(
            user_id=user_id, skip=skip, limit=limit
        )
        return [ReviewResponse.model_validate(r) for r in reviews]

    async def get_user_course_review(
        self, user_id: int, course_id: int
    ) -> ReviewResponse:
        """
        Get a specific user's review for a course.

        Args:
            user_id: The ID of the user.
            course_id: The ID of the course.

        Returns:
            ReviewResponse: The found review.

        Raises:
            HTTPException: 404 if the review does not exist.
        """
        review = await self.review_repo.get(user_id=user_id, course_id=course_id)
        if not review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Review not found for this course",
            )
        return ReviewResponse.model_validate(review)

    async def update_review(
        self, user_id: int, review_id: int, review_in: ReviewUpdate
    ) -> ReviewResponse:
        """
        Update an existing review.

        Verifies that the user attempting the update is the original author.

        Args:
            user_id: ID of the user attempting the update.
            review_id: ID of the review to be updated.
            review_in: The updated review data.

        Returns:
            Review: The updated review object.

        Raises:
            HTTPException: 403 if the user is not the author.
            HTTPException: 404 if the review is not found.
        """
        review = await self._get_review_db(review_id)

        if review.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this review",
            )

        if review_in.rating is not None:
            review.rating = review_in.rating
        if review_in.comment is not None:
            review.comment = review_in.comment

        review.updated_at = datetime.now(timezone.utc)
        updated_review = await self.review_repo.update(review)
        get_cached_summary.cache_invalidate(review.course_id, self.review_repo)
        return ReviewResponse.model_validate(updated_review)

    async def delete_review(self, user_id: int, review_id: int) -> None:
        """
        Delete a review by its ID.

        Verifies that the user attempting the deletion is the original author.

        Args:
            user_id: ID of the user attempting the deletion.
            review_id: ID of the review to be deleted.

        Raises:
            HTTPException: 403 if the user is not the author.
            HTTPException: 404 if the review is not found.
        """
        review = await self._get_review_db(review_id)

        if review.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this review",
            )

        await self.review_repo.delete(review)
        get_cached_summary.cache_invalidate(review.course_id, self.review_repo)

    async def _get_review_db(self, review_id: int) -> Review:
        """Internal helper to get database model for review."""
        review = await self.review_repo.get(review_id=review_id)
        if not review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Review not found"
            )
        return review

    async def get_course_summary(self, course_id: int) -> dict:
        """
        Get a summary of reviews (average and count) for a course.

        Args:
            course_id: The ID of the course.

        Returns:
            dict: Summary containing 'average_rating' and 'total_reviews'.
        """
        return await self.review_repo.get_course_summary(course_id)
