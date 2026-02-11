"""Course API endpoints."""

from fastapi import APIRouter, Depends, status, HTTPException, Query, BackgroundTasks
from typing import List
import traceback
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.database.session import get_async_session
from app.common.deps import get_current_active_user, get_current_active_user_optional
from app.common.responses import ApiResponse, success_response
from app.features.users.models import User
from app.common.dependencies import (
    get_course_service,
    get_category_service,
    get_subcategory_service,
    get_course_generation_service,
    run_db_maintenance_in_bg,
)
from app.features.subscriptions.dependencies import (
    ResourceAccessControl,
    get_user_subscription,
    get_subscription_usage_service,
    get_premium_user,
)
from app.features.subscriptions.usage_service import SubscriptionUsageService
from app.features.subscriptions.models import Subscription, SubscriptionResourceType
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
    CoursePublishRequest,
)
from app.features.courses.models import UserCourse, CourseLevel
from app.features.courses.service import (
    CourseService,
    CategoryService,
    SubCategoryService,
)
from app.features.courses.generation_service import CourseGenerationService
from app.features.courses.tasks import generate_course_image_background

router = APIRouter()


@router.post("/generate", response_model=ApiResponse[CourseGenerationResponse])
async def generate_courses(
    request: CourseGenerationRequest,
    current_user: User = Depends(get_current_active_user),
    _access: None = Depends(ResourceAccessControl(SubscriptionResourceType.JOURNEY)),
    subscription: Subscription = Depends(get_user_subscription),
    usage_service: SubscriptionUsageService = Depends(get_subscription_usage_service),
    service: CourseGenerationService = Depends(get_course_generation_service),
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
        # Generate courses via service
        outlines = await service.generate_courses(request, usage_service, subscription)

        # Set the level for each generated course
        for outline in outlines:
            outline.level = request.level

        return success_response(
            data=CourseGenerationResponse(courses=outlines),
            details=f"Successfully generated {len(outlines)} course(s)",
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
    service: CourseService = Depends(get_course_service),
    current_user: User = Depends(get_current_active_user),
):
    """
    Create a new course from a generated outline.

    This endpoint takes a CourseOutline (likely from the /generate endpoint)
    and persists it to the database, creating the course, modules, and lessons.
    """
    try:
        assert current_user.id  # Ensure user has an ID
        course = await service.create_course(current_user.id, course_data)

        # Enroll the creator in the course (optional: could pass usage here too if tracking)
        assert course.id
        await service.enroll_course(current_user.id, course.id)

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
    service: CourseService = Depends(get_course_service),
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
    service: CourseService = Depends(get_course_service),
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


@router.post("/{course_id}/publish", response_model=ApiResponse[CourseResponse])
async def publish_course(
    course_id: int,
    publish_data: CoursePublishRequest,
    background_tasks: BackgroundTasks,
    service: CourseService = Depends(get_course_service),
    current_user: User = Depends(get_premium_user),
):
    """
    Publish a course to make it public.

    This endpoint updates the course to be public and assigns it to a category.
    If the course doesn't have an image, one will be generated in the background.

    **Authentication required** - only course creator can publish.
    """
    try:
        assert current_user.id  # Ensure user has an ID

        update_data = {
            "category_id": publish_data.category_id,
            "sub_category_id": publish_data.sub_category_id,
            "is_public": True,
        }

        updated_course = await service.update_course(
            user_id=current_user.id,
            course_id=course_id,
            course_update=update_data,
        )

        # Generate image in background if it's missing
        if not updated_course.image_url:
            background_tasks.add_task(
                generate_course_image_background, course_id, service
            )

        return success_response(
            data=updated_course,
            details="Course published successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to publish course: {str(e)}",
        )


@router.post("/{course_id}/unpublish", response_model=ApiResponse[CourseResponse])
async def unpublish_course(
    course_id: int,
    service: CourseService = Depends(get_course_service),
    current_user: User = Depends(get_premium_user),
):
    """
    Unpublish a course to make it private.

    This endpoint updates the course to be private (is_public=False).
    Unpublishing is only allowed if the course has 1 or fewer enrollees.

    **Authentication required** - only course creator can unpublish.
    """
    try:
        assert current_user.id  # Ensure user has an ID

        updated_course = await service.unpublish_course(
            user_id=current_user.id,
            course_id=course_id,
        )

        return success_response(
            data=updated_course,
            details="Course unpublished successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unpublish course: {str(e)}",
        )


@router.post("/{course_id}/enroll", response_model=ApiResponse[UserCourseResponse])
async def enroll_course(
    course_id: int,
    service: CourseService = Depends(get_course_service),
    current_user: User = Depends(get_current_active_user),
    _access: None = Depends(ResourceAccessControl(SubscriptionResourceType.JOURNEY)),
    subscription: Subscription = Depends(get_user_subscription),
    usage_service: SubscriptionUsageService = Depends(get_subscription_usage_service),
):
    """
    Enroll the current user in a course.

    Creates a UserCourse record if one doesn't exist.
    """
    try:
        assert current_user.id  # Ensure user has an ID
        user_course = await service.enroll_course(
            current_user.id, course_id, usage_service, subscription
        )

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
    search: str | None = Query(None, description="Search for a course by title"),
    level: CourseLevel | None = Query(None, description="Filter by course level"),
    service: CourseService = Depends(get_course_service),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get all courses enrolled by the current user.

    Returns paginated list of user's enrolled courses with:
    - Course details
    - Enrollment status
    - Progress information

    **Note:** Most recently updated or enrolled courses appear first.

    **Authentication required.**
    """
    try:
        assert current_user.id  # Ensure user has an ID
        user_courses = await service.get_user_courses(
            user_id=current_user.id,
            page=page,
            per_page=per_page,
            search=search,
            level=level,
        )

        return success_response(
            data=PaginatedUserCoursesResponse(
                courses=user_courses,
                page=page,
                per_page=per_page,
                total=len(user_courses),
            ),
            details=f"Retrieved {len(user_courses)} enrolled course(s)",
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch user courses: {str(e)}",
        )


@router.get("/user/courses/detail", response_model=ApiResponse[UserCourseResponse])
async def get_user_course_detail(
    course_id: int = Query(..., description="ID of the course"),
    service: CourseService = Depends(get_course_service),
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
        user_course = await service.get_user_course_detail(
            user_id=current_user.id,
            course_id=course_id,
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


# Category Endpoints


@router.post("/categories", response_model=ApiResponse[CategoryResponse])
async def create_category(
    category_data: CategoryCreate,
    service: CategoryService = Depends(get_category_service),
    current_user: User = Depends(get_current_active_user),
):
    """
    Create a new category.

    **Authentication required.**
    """
    try:
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
    service: CategoryService = Depends(get_category_service),
):
    """
    Get all categories.

    **No authentication required.**
    """
    try:
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
    service: CategoryService = Depends(get_category_service),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update a category.

    **Authentication required.**
    """
    try:
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
    service: CategoryService = Depends(get_category_service),
    current_user: User = Depends(get_current_active_user),
):
    """
    Delete a category.

    **Authentication required.**
    """
    try:
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
    service: SubCategoryService = Depends(get_subcategory_service),
    current_user: User = Depends(get_current_active_user),
):
    """
    Create a new sub-category.

    **Authentication required.**
    """
    try:
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
    service: SubCategoryService = Depends(get_subcategory_service),
):
    """
    Get all sub-categories, optionally filtered by category.

    **No authentication required.**
    """
    try:
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
    service: SubCategoryService = Depends(get_subcategory_service),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update a sub-category.

    **Authentication required.**
    """
    try:
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
    service: SubCategoryService = Depends(get_subcategory_service),
    current_user: User = Depends(get_current_active_user),
):
    """
    Delete a sub-category.

    **Authentication required.**
    """
    try:
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


# General course endpoints
@router.get("", response_model=ApiResponse[PaginatedCoursesResponse])
async def get_courses(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    is_public: bool | None = Query(None, description="Filter by public/private"),
    level: CourseLevel | None = Query(None, description="Filter by course level"),
    category_id: int | None = Query(None, description="Filter by category ID"),
    min_enrollees: int | None = Query(None, ge=0, description="Minimum enrollees"),
    search: str | None = Query(None, description="Search for a course by title"),
    service: CourseService = Depends(get_course_service),
    _maintenance: None = Depends(run_db_maintenance_in_bg),
):
    """
    Get all courses with pagination and optional filters.

    Courses are ordered by total enrollees (highest first).

    **Query Parameters:**
    - `page`: Page number (default: 1)
    - `per_page`: Items per page (default: 10, max: 100)
    - `is_public`: Filter by public courses (optional)
    - `level`: Filter by course level (beginner, intermediate, expert) (optional)
    - `min_enrollees`: Filter by minimum number of enrollees (optional)

    **No authentication required** - returns public courses by default.
    """
    try:
        courses = await service.get_courses(
            page=page,
            per_page=per_page,
            is_public=is_public,
            level=level,
            category_id=category_id,
            min_enrollees=min_enrollees,
            search=search,
        )

        return success_response(
            data=PaginatedCoursesResponse(
                courses=courses,
                page=page,
                per_page=per_page,
                total=len(courses),
            ),
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
    background_tasks: BackgroundTasks,
    service: CourseService = Depends(get_course_service),
    current_user: User | None = Depends(get_current_active_user_optional),
    _maintenance: None = Depends(run_db_maintenance_in_bg),
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
        course = await service.get_course_detail(course_id)

        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found",
            )

        # Access check: if private, only creator can access
        if not course.is_public:
            if not current_user or current_user.id != course.user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Course cannot be accessed",
                )

        # Generate image in background if it's missing
        if not course.image_url:
            background_tasks.add_task(
                generate_course_image_background, course_id, service
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
