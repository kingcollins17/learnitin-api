"""Course API endpoints."""

from fastapi import APIRouter, Depends, status, HTTPException, Query
from typing import List
import traceback
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.database.session import get_async_session
from app.common.deps import get_current_active_user
from app.common.responses import ApiResponse, success_response
from app.features.users.models import User
from app.features.courses.schemas import (
    CourseGenerationRequest,
    CourseGenerationResponse,
    CourseOutline,
    CourseResponse,
    CourseUpdate,
    CourseDetailResponse,
    UserCourseResponse,
    PaginatedCoursesResponse,
    PaginatedUserCoursesResponse,
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
    SubCategoryCreate,
    SubCategoryResponse,
    SubCategoryUpdate,
)
from app.features.courses.models import UserCourse
from app.features.courses.service import (
    CourseService,
    CategoryService,
    SubCategoryService,
)
from app.features.courses.generation_service import CourseGenerationService

router = APIRouter()


@router.post("/generate", response_model=ApiResponse[CourseGenerationResponse])
async def generate_courses(
    request: CourseGenerationRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Generate personalized course curricula using AI.

    This endpoint uses LangChain to generate comprehensive course outlines
    based on the user's specified topic, level, and learning goals.

    The generated courses are NOT saved to the database - they are created
    on-demand for the user to review.

    **Authentication required.**
    """
    try:
        generation_service = CourseGenerationService()
        courses = await generation_service.generate_courses(request)

        return success_response(
            data=CourseGenerationResponse(courses=courses),
            details=f"Successfully generated {len(courses)} course(s)",
        )
    except HTTPException:
        traceback.print_exc()
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate courses: {str(e)}",
        )


@router.post("/create", response_model=ApiResponse[CourseResponse])
async def create_course(
    course_data: CourseOutline,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Create a new course from a generated outline.

    This endpoint takes a CourseOutline (likely from the /generate endpoint)
    and persists it to the database, creating the course, modules, and lessons.
    """
    try:
        assert current_user.id  # Ensure user has an ID
        service = CourseService(session)
        course = await service.create_course(current_user.id, course_data)

        return success_response(data=course, details="Course created successfully")
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create course: {str(e)}",
        )


@router.patch("/{course_id}", response_model=ApiResponse[CourseResponse])
async def update_course(
    course_id: int,
    course_update: CourseUpdate,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update a course.

    Only the course creator can update their course.
    You can update the following fields:
    - title
    - description
    - duration
    - is_public

    **Authentication required** - only course creator can update.
    """
    try:
        assert current_user.id  # Ensure user has an ID
        service = CourseService(session)

        # Convert Pydantic model to dict, excluding unset fields
        update_data = course_update.model_dump(exclude_unset=True)

        updated_course = await service.update_course(
            user_id=current_user.id,
            course_id=course_id,
            course_update=update_data,
        )

        return success_response(
            data=updated_course,
            details="Course updated successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update course: {str(e)}",
        )


@router.delete("/{course_id}", response_model=ApiResponse[dict])
async def delete_course(
    course_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Delete a course.

    Only the course creator can delete their course.
    This will also delete all associated modules and lessons.

    **Authentication required** - only course creator can delete.
    """
    try:
        assert current_user.id  # Ensure user has an ID
        service = CourseService(session)

        await service.delete_course(
            user_id=current_user.id,
            course_id=course_id,
        )

        return success_response(
            data={"course_id": course_id},
            details="Course deleted successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete course: {str(e)}",
        )


@router.post("/{course_id}/enroll", response_model=ApiResponse[UserCourse])
async def enroll_course(
    course_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Enroll the current user in a course.

    Creates a UserCourse record if one doesn't exist.
    """
    try:
        assert current_user.id  # Ensure user has an ID
        service = CourseService(session)
        user_course = await service.enroll_course(current_user.id, course_id)

        return success_response(
            data=user_course, details="Successfully enrolled in course"
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enroll in course: {str(e)}",
        )


# User course endpoints (must come before /{course_id} to avoid path conflicts)
@router.get("/user/courses", response_model=ApiResponse[PaginatedUserCoursesResponse])
async def get_user_courses(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get all courses enrolled by the current user.

    Returns paginated list of user's enrolled courses with:
    - Course details
    - Enrollment status
    - Progress information

    **Authentication required.**
    """
    try:
        assert current_user.id  # Ensure user has an ID
        service = CourseService(session)
        user_courses = await service.get_user_courses(
            user_id=current_user.id,
            page=page,
            per_page=per_page,
        )

        # Convert SQLModel objects to Pydantic schemas
        user_courses_response = [
            UserCourseResponse.model_validate(uc) for uc in user_courses
        ]

        response_data = PaginatedUserCoursesResponse(
            courses=user_courses_response,
            page=page,
            per_page=per_page,
            total=len(user_courses),
        )

        return success_response(
            data=response_data,
            details=f"Retrieved {len(user_courses)} enrolled course(s)",
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch user courses: {str(e)}",
        )


@router.get(
    "/user/courses/{user_course_id}", response_model=ApiResponse[UserCourseResponse]
)
async def get_user_course_detail(
    user_course_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get detailed information about a specific user course enrollment.

    Returns:
    - Course details
    - Enrollment status
    - Progress information
    - Current lesson

    **Authentication required** - users can only access their own enrollments.
    """
    try:
        assert current_user.id  # Ensure user has an ID
        service = CourseService(session)
        user_course = await service.get_user_course_detail(
            user_id=current_user.id,
            user_course_id=user_course_id,
        )

        return success_response(
            data=user_course,
            details="User course details retrieved successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch user course details: {str(e)}",
        )


# General course endpoints
@router.get("", response_model=ApiResponse[PaginatedCoursesResponse])
async def get_courses(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    is_public: bool | None = Query(None, description="Filter by public/private"),
    level: str | None = Query(None, description="Filter by course level"),
    category_id: int | None = Query(None, description="Filter by category ID"),
    min_enrollees: int | None = Query(None, ge=0, description="Minimum enrollees"),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get all courses with pagination and optional filters.

    **Query Parameters:**
    - `page`: Page number (default: 1)
    - `per_page`: Items per page (default: 10, max: 100)
    - `is_public`: Filter by public courses (optional)
    - `level`: Filter by course level (beginner, intermediate, expert) (optional)
    - `min_enrollees`: Filter by minimum number of enrollees (optional)

    **No authentication required** - returns public courses by default.
    """
    try:
        service = CourseService(session)
        courses = await service.get_courses(
            page=page,
            per_page=per_page,
            is_public=is_public,
            level=level,
            category_id=category_id,
            min_enrollees=min_enrollees,
        )

        # Convert SQLModel objects to Pydantic schemas
        courses_response = [CourseResponse.model_validate(c) for c in courses]

        response_data = PaginatedCoursesResponse(
            courses=courses_response,
            page=page,
            per_page=per_page,
            total=len(courses),
        )

        return success_response(
            data=response_data,
            details=f"Retrieved {len(courses)} course(s)",
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch courses: {str(e)}",
        )


@router.get("/{course_id}", response_model=ApiResponse[CourseDetailResponse])
async def get_course_detail(
    course_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get course detail with all modules and lessons.

    Returns the complete course structure including:
    - Course metadata
    - All modules in order
    - All lessons within each module

    **No authentication required** for public courses.
    """
    try:
        service = CourseService(session)
        course = await service.get_course_detail(course_id)

        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found",
            )

        return success_response(
            data=course,
            details="Course details retrieved successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch course details: {str(e)}",
        )


# Category Endpoints


@router.post("/categories", response_model=ApiResponse[CategoryResponse])
async def create_category(
    category_data: CategoryCreate,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Create a new category.

    **Authentication required.**
    """
    try:
        service = CategoryService(session)
        category = await service.create_category(category_data.model_dump())

        return success_response(
            data=category,
            details="Category created successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create category: {str(e)}",
        )


@router.get("/categories", response_model=ApiResponse[List[CategoryResponse]])
async def get_categories(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(100, ge=1, le=100, description="Items per page"),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get all categories.

    **No authentication required.**
    """
    try:
        service = CategoryService(session)
        categories = await service.get_categories(page=page, per_page=per_page)

        return success_response(
            data=categories,
            details=f"Retrieved {len(categories)} categories",
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch categories: {str(e)}",
        )


@router.patch("/categories/{category_id}", response_model=ApiResponse[CategoryResponse])
async def update_category(
    category_id: int,
    category_update: CategoryUpdate,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update a category.

    **Authentication required.**
    """
    try:
        service = CategoryService(session)
        updated_category = await service.update_category(
            category_id,
            category_update.model_dump(exclude_unset=True),
        )

        return success_response(
            data=updated_category,
            details="Category updated successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update category: {str(e)}",
        )


@router.delete("/categories/{category_id}", response_model=ApiResponse[dict])
async def delete_category(
    category_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Delete a category.

    **Authentication required.**
    """
    try:
        service = CategoryService(session)
        await service.delete_category(category_id)

        return success_response(
            data={"category_id": category_id},
            details="Category deleted successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete category: {str(e)}",
        )


# SubCategory Endpoints


@router.post("/sub-categories", response_model=ApiResponse[SubCategoryResponse])
async def create_subcategory(
    sub_category_data: SubCategoryCreate,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Create a new sub-category.

    **Authentication required.**
    """
    try:
        service = SubCategoryService(session)
        sub_category = await service.create_subcategory(sub_category_data.model_dump())

        return success_response(
            data=sub_category,
            details="Sub-category created successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create sub-category: {str(e)}",
        )


@router.get("/sub-categories", response_model=ApiResponse[List[SubCategoryResponse]])
async def get_subcategories(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(100, ge=1, le=100, description="Items per page"),
    category_id: int | None = Query(None, description="Filter by category ID"),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get all sub-categories, optionally filtered by category.

    **No authentication required.**
    """
    try:
        service = SubCategoryService(session)
        sub_categories = await service.get_subcategories(
            page=page, per_page=per_page, category_id=category_id
        )

        return success_response(
            data=sub_categories,
            details=f"Retrieved {len(sub_categories)} sub-categories",
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch sub-categories: {str(e)}",
        )


@router.patch(
    "/sub-categories/{sub_category_id}", response_model=ApiResponse[SubCategoryResponse]
)
async def update_subcategory(
    sub_category_id: int,
    sub_category_update: SubCategoryUpdate,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update a sub-category.

    **Authentication required.**
    """
    try:
        service = SubCategoryService(session)
        updated_sub_category = await service.update_subcategory(
            sub_category_id,
            sub_category_update.model_dump(exclude_unset=True),
        )

        return success_response(
            data=updated_sub_category,
            details="Sub-category updated successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update sub-category: {str(e)}",
        )


@router.delete("/sub-categories/{sub_category_id}", response_model=ApiResponse[dict])
async def delete_subcategory(
    sub_category_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Delete a sub-category.

    **Authentication required.**
    """
    try:
        service = SubCategoryService(session)
        await service.delete_subcategory(sub_category_id)

        return success_response(
            data={"sub_category_id": sub_category_id},
            details="Sub-category deleted successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete sub-category: {str(e)}",
        )
