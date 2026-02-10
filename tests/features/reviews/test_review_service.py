"""Tests for Review Service."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException, status
from datetime import datetime, timezone
from app.features.reviews.service import ReviewService
from app.features.reviews.models import Review
from app.features.reviews.schemas import ReviewCreate, ReviewUpdate
from app.features.courses.models import Course


class TestReviewService:
    """Test suite for ReviewService."""

    @pytest.fixture
    def mock_session(self):
        """Mock AsyncSession for database operations."""
        return AsyncMock()

    @pytest.fixture
    def mock_review_repo(self):
        """Mock ReviewRepository to isolate service logic from DB."""
        return AsyncMock()

    @pytest.fixture
    def mock_course_repo(self):
        """Mock CourseRepository to isolate service logic from DB."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_session, mock_review_repo, mock_course_repo):
        """Create ReviewService instance with mocked dependencies."""
        return ReviewService(
            session=mock_session,
            review_repo=mock_review_repo,
            course_repo=mock_course_repo,
        )

    @pytest.mark.asyncio
    async def test_create_review_success(
        self, service, mock_review_repo, mock_course_repo
    ):
        """Test successful review creation."""
        # --- Arrange ---
        user_id = 1
        course_id = 10
        review_in = ReviewCreate(course_id=course_id, rating=5, comment="Great course!")

        # Mock that the course exists
        mock_course_repo.get_by_id.return_value = MagicMock(spec=Course, id=course_id)
        # Mock that no existing review exists for this user/course combo
        mock_review_repo.get.return_value = None
        # Mock create to return whatever review is passed into it
        mock_review_repo.create.side_effect = lambda r: r

        # --- Act ---
        review = await service.create_review(user_id=user_id, review_in=review_in)

        # --- Assert ---
        assert review.user_id == user_id
        assert review.course_id == course_id
        assert review.rating == 5
        assert review.comment == "Great course!"

        # Verify repository interactions
        mock_course_repo.get_by_id.assert_called_once_with(course_id)
        mock_review_repo.get.assert_called_once_with(
            user_id=user_id, course_id=course_id
        )
        mock_review_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_review_course_not_found(self, service, mock_course_repo):
        """Test review creation fails when target course does not exist."""
        # --- Arrange ---
        user_id = 1
        review_in = ReviewCreate(course_id=999, rating=5)

        # Mock that the course lookup returns None (not found)
        mock_course_repo.get_by_id.return_value = None

        # --- Act & Assert ---
        with pytest.raises(HTTPException) as exc:
            await service.create_review(user_id=user_id, review_in=review_in)

        assert exc.value.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in exc.value.detail.lower()

    @pytest.mark.asyncio
    async def test_create_review_already_exists(
        self, service, mock_review_repo, mock_course_repo
    ):
        """Test review creation fails if user has already reviewed the course."""
        # --- Arrange ---
        user_id = 1
        course_id = 10
        review_in = ReviewCreate(course_id=course_id, rating=5)

        # Mock that the course exists
        mock_course_repo.get_by_id.return_value = MagicMock(spec=Course, id=course_id)
        # Mock that a review ALREADY exists for this user/course combo
        mock_review_repo.get.return_value = MagicMock(spec=Review)

        # --- Act & Assert ---
        with pytest.raises(HTTPException) as exc:
            await service.create_review(user_id=user_id, review_in=review_in)

        assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "already reviewed" in exc.value.detail.lower()

    @pytest.mark.asyncio
    async def test_get_review_success(self, service, mock_review_repo):
        """Test retrieving a single review by its ID."""
        # --- Arrange ---
        review_id = 1
        mock_review = Review(
            id=review_id,
            user_id=1,
            course_id=10,
            rating=5,
            comment="Test",
            created_at=datetime.now(timezone.utc),
        )
        mock_review_repo.get.return_value = mock_review

        # --- Act ---
        review = await service.get_review(review_id)

        # --- Assert ---
        assert review.id == review_id
        assert review.rating == 5
        mock_review_repo.get.assert_called_once_with(review_id=review_id)

    @pytest.mark.asyncio
    async def test_get_review_not_found(self, service, mock_review_repo):
        """Test error when retrieving a non-existent review ID."""
        # --- Arrange ---
        mock_review_repo.get.return_value = None

        # --- Act & Assert ---
        with pytest.raises(HTTPException) as exc:
            await service.get_review(999)

        assert exc.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_update_review_success(self, service, mock_review_repo):
        """Test successful update when the user is the original author."""
        # --- Arrange ---
        user_id = 1
        review_id = 5
        # Mock a review belonging to user_id=1
        mock_review = Review(
            id=review_id,
            user_id=user_id,
            course_id=10,
            rating=3,
            created_at=datetime.now(timezone.utc),
        )
        mock_review_repo.get.return_value = mock_review
        mock_review_repo.update.side_effect = lambda r: r

        update_in = ReviewUpdate(rating=5, comment="Updated!")

        # --- Act ---
        updated_review = await service.update_review(user_id, review_id, update_in)

        # --- Assert ---
        assert updated_review.rating == 5
        assert updated_review.comment == "Updated!"
        mock_review_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_review_unauthorized(self, service, mock_review_repo):
        """Test update blocked when user is NOT the original author."""
        # --- Arrange ---
        user_id = 1  # Attacker/Someone else
        author_id = 2  # Original author
        review_id = 5
        # Mock a review belonging to author_id=2
        mock_review = MagicMock(spec=Review, id=review_id, user_id=author_id)
        mock_review_repo.get.return_value = mock_review

        update_in = ReviewUpdate(rating=5)

        # --- Act & Assert ---
        with pytest.raises(HTTPException) as exc:
            await service.update_review(user_id, review_id, update_in)

        assert exc.value.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_delete_review_success(self, service, mock_review_repo):
        """Test successful deletion when the user is the author."""
        # --- Arrange ---
        user_id = 1
        review_id = 5
        mock_review = MagicMock(spec=Review, id=review_id, user_id=user_id)
        mock_review_repo.get.return_value = mock_review

        # --- Act ---
        await service.delete_review(user_id, review_id)

        # --- Assert ---
        mock_review_repo.delete.assert_called_once_with(mock_review)

    @pytest.mark.asyncio
    async def test_delete_review_unauthorized(self, service, mock_review_repo):
        """Test deletion blocked when user is NOT the author."""
        # --- Arrange ---
        user_id = 1
        author_id = 2
        review_id = 5
        mock_review = MagicMock(spec=Review, id=review_id, user_id=author_id)
        mock_review_repo.get.return_value = mock_review

        # --- Act & Assert ---
        with pytest.raises(HTTPException) as exc:
            await service.delete_review(user_id, review_id)

        assert exc.value.status_code == status.HTTP_403_FORBIDDEN
        mock_review_repo.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_course_reviews(self, service, mock_review_repo):
        """Test retrieving a list of reviews for a course."""
        # --- Arrange ---
        course_id = 10
        mock_reviews = [
            Review(
                id=1,
                user_id=1,
                course_id=course_id,
                rating=5,
                created_at=datetime.now(timezone.utc),
            ),
            Review(
                id=2,
                user_id=2,
                course_id=course_id,
                rating=4,
                created_at=datetime.now(timezone.utc),
            ),
        ]
        mock_review_repo.get_all.return_value = mock_reviews

        # --- Act ---
        reviews = await service.get_course_reviews(course_id, skip=0, limit=10)

        # --- Assert ---
        assert len(reviews) == 2
        assert reviews[0].rating == 5
        assert reviews[1].rating == 4
        mock_review_repo.get_all.assert_called_once_with(
            course_id=course_id, skip=0, limit=10
        )

    @pytest.mark.asyncio
    async def test_get_user_reviews(self, service, mock_review_repo):
        """Test retrieving all reviews written by a specific user."""
        # --- Arrange ---
        user_id = 1
        mock_reviews = [
            Review(
                id=1,
                user_id=user_id,
                course_id=10,
                rating=5,
                created_at=datetime.now(timezone.utc),
            )
        ]
        mock_review_repo.get_all.return_value = mock_reviews

        # --- Act ---
        reviews = await service.get_user_reviews(user_id, skip=0, limit=10)

        # --- Assert ---
        assert len(reviews) == 1
        assert reviews[0].rating == 5
        mock_review_repo.get_all.assert_called_once_with(
            user_id=user_id, skip=0, limit=10
        )

    @pytest.mark.asyncio
    async def test_get_course_summary(self, service, mock_review_repo):
        """Test retrieving a review summary for a course."""
        # --- Arrange ---
        course_id = 10
        mock_summary = {"average_rating": 4.5, "total_reviews": 10}
        mock_review_repo.get_course_summary.return_value = mock_summary

        # --- Act ---
        summary = await service.get_course_summary(course_id)

        # --- Assert ---
        assert summary == mock_summary
        mock_review_repo.get_course_summary.assert_called_once_with(course_id)
