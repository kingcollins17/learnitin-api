"""Review API endpoints."""

from fastapi import APIRouter, Depends, status, Query
from typing import List
from app.common.responses import ApiResponse, success_response
from app.common.deps import get_current_active_user
from app.features.users.models import User
from app.features.reviews.schemas import (
    ReviewCreate,
    ReviewUpdate,
    ReviewResponse,
    ReviewSummary,
)
from app.features.reviews.service import ReviewService
from app.features.reviews.dependencies import get_review_service

router = APIRouter()


@router.post(
    "/",
    response_model=ApiResponse[ReviewResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_review(
    review_in: ReviewCreate,
    current_user: User = Depends(get_current_active_user),
    service: ReviewService = Depends(get_review_service),
):
    """
    Create a new course review.

    Allows an authenticated and active user to rate and comment on a course.

    **Constraints:**
    - Only one review permitted per course per user.
    - Rating must be an integer between 1 and 5.
    - The `course_id` must refer to an existing course.

    **Authentication:**
    - Required (Bearer Token)
    - User account must be active.
    """
    assert current_user.id is not None
    review = await service.create_review(user_id=current_user.id, review_in=review_in)
    return success_response(
        data=review,
        details="Review created successfully",
        status_code=201,
    )


@router.get(
    "/course/{course_id}",
    response_model=ApiResponse[List[ReviewResponse]],
)
async def get_course_reviews(
    course_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    service: ReviewService = Depends(get_review_service),
):
    """
    Get reviews for a specific course.

    Returns a paginated list of reviews associated with the given `course_id`.

    **Pagination:**
    - `page`: Page number (default: 1).
    - `per_page`: Maximum number of reviews per page (default: 10, max: 100).
    """
    skip = (page - 1) * per_page
    limit = per_page
    reviews = await service.get_course_reviews(course_id, skip, limit)
    return success_response(data=reviews)


@router.get(
    "/course/{course_id}/me",
    response_model=ApiResponse[ReviewResponse],
)
async def get_user_course_review(
    course_id: int,
    current_user: User = Depends(get_current_active_user),
    service: ReviewService = Depends(get_review_service),
):
    """
    Get current user's review for a specific course.

    Returns the review record if the current user has reviewed the course.

    **Authentication:**
    - Required (Bearer Token)
    """
    assert current_user.id is not None
    review = await service.get_user_course_review(
        user_id=current_user.id, course_id=course_id
    )
    return success_response(data=review)


@router.get(
    "/course/{course_id}/summary",
    response_model=ApiResponse[ReviewSummary],
)
async def get_course_review_summary(
    course_id: int,
    service: ReviewService = Depends(get_review_service),
):
    """
    Get a summary of reviews for a course.

    Returns the average rating and total number of reviews for the given `course_id`.
    """
    summary = await service.get_course_summary(course_id)
    return success_response(data=ReviewSummary(**summary))


@router.get(
    "/me",
    response_model=ApiResponse[List[ReviewResponse]],
)
async def get_my_reviews(
    current_user: User = Depends(get_current_active_user),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    service: ReviewService = Depends(get_review_service),
):
    """
    Get current user's reviews.

    Returns a paginated list of all reviews written by the currently authenticated user.

    **Pagination:**
    - `page`: Page number (default: 1).
    - `per_page`: Maximum number of reviews per page (default: 10, max: 100).

    **Authentication:**
    - Required (Bearer Token)
    """
    assert current_user.id is not None
    skip = (page - 1) * per_page
    limit = per_page
    reviews = await service.get_user_reviews(current_user.id, skip, limit)
    return success_response(data=reviews)


@router.patch(
    "/{review_id}",
    response_model=ApiResponse[ReviewResponse],
)
async def update_review(
    review_id: int,
    review_in: ReviewUpdate,
    current_user: User = Depends(get_current_active_user),
    service: ReviewService = Depends(get_review_service),
):
    """
    Update an existing review.

    Allows the author of a review to update their rating or comment.

    **Permissions:**
    - Only the author of the review can perform this action.
    - Review must exist.

    **Authentication:**
    - Required (Bearer Token)
    """
    assert current_user.id is not None
    review = await service.update_review(
        user_id=current_user.id, review_id=review_id, review_in=review_in
    )
    return success_response(
        data=review,
        details="Review updated successfully",
    )


@router.delete(
    "/{review_id}",
    response_model=ApiResponse[bool],
)
async def delete_review(
    review_id: int,
    current_user: User = Depends(get_current_active_user),
    service: ReviewService = Depends(get_review_service),
):
    """
    Delete a review.

    Permanently removes the review with the specified ID.

    **Permissions:**
    - Only the author of the review can perform this action.
    - Review must exist.

    **Authentication:**
    - Required (Bearer Token)
    """
    assert current_user.id is not None
    await service.delete_review(user_id=current_user.id, review_id=review_id)
    return success_response(data=True, details="Review deleted successfully")
