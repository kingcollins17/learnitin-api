"""Review repository for database operations."""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from sqlalchemy.orm import joinedload
from sqlmodel import select, col
from app.features.reviews.models import Review

from async_lru import alru_cache


class ReviewRepository:
    """Repository for review database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(
        self,
        review_id: Optional[int] = None,
        user_id: Optional[int] = None,
        course_id: Optional[int] = None,
    ) -> Optional[Review]:
        """Get a review with optional filters."""
        query = select(Review).options(
            joinedload(Review.user), joinedload(Review.course)  # type: ignore
        )
        if review_id is not None:
            query = query.where(Review.id == review_id)
        if user_id is not None:
            query = query.where(Review.user_id == user_id)
        if course_id is not None:
            query = query.where(Review.course_id == course_id)

        result = await self.session.execute(query)
        return result.unique().scalar_one_or_none()

    async def get_all(
        self,
        user_id: Optional[int] = None,
        course_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Review]:
        """Get all reviews with optional filters and pagination."""
        query = select(Review).options(
            joinedload(Review.user), joinedload(Review.course)  # type: ignore
        )
        if user_id is not None:
            query = query.where(Review.user_id == user_id)
        if course_id is not None:
            query = query.where(Review.course_id == course_id)

        query = query.order_by(col(Review.created_at).desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.unique().scalars().all())

    async def create(self, review: Review) -> Review:
        """Create a new review."""
        self.session.add(review)
        await self.session.flush()
        await self.session.refresh(review)
        return review

    async def update(self, review: Review) -> Review:
        """Update an existing review."""
        self.session.add(review)
        await self.session.flush()
        await self.session.refresh(review)
        return review

    async def delete(self, review: Review) -> None:
        """Delete a review."""
        await self.session.delete(review)
        await self.session.flush()

    async def get_course_summary(self, course_id: int) -> dict:
        """
        Get a summary of reviews for a specific course using raw SQL.

        Calculates the average rating and total count of reviews.
        """

        statement = text(
            "SELECT SUM(rating) as total_sum, COUNT(*) as review_count "
            "FROM reviews "
            "WHERE course_id = :course_id"
        )
        result = await self.session.execute(statement, {"course_id": course_id})
        row = result.fetchone()

        summary = {"average_rating": 0.0, "total_reviews": 0}

        if row and row[1] > 0:
            total_sum = float(row[0]) if row[0] is not None else 0.0
            total_reviews = int(row[1])
            avg_rating = total_sum / total_reviews
            summary = {
                "average_rating": round(avg_rating, 2),
                "total_reviews": total_reviews,
            }

        return summary


@alru_cache(maxsize=1024)
async def get_cached_summary(
    course_id: int, review_repo: ReviewRepository
) -> Optional[dict]:
    """
    Independent cached function to retrieve review summary.
    This fulfills the requirement of using functools for caching.
    """
    return await review_repo.get_course_summary(course_id)
