"""Module API endpoints."""

from fastapi import APIRouter, Depends, status, HTTPException, Query
from typing import List
import traceback
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.database.session import get_async_session
from app.common.deps import get_current_active_user
from app.common.responses import ApiResponse, success_response
from app.features.users.models import User
from app.features.modules.schemas import (
    ModuleResponse,
    ModuleCreate,
    ModuleUpdate,
    PaginatedModulesResponse,
    UserModuleResponse,
    UserModuleCreate,
    UserModuleUpdate,
    PaginatedUserModulesResponse,
)
from app.features.modules.service import ModuleService, UserModuleService

router = APIRouter()


# Module Endpoints


@router.get("", response_model=ApiResponse[PaginatedModulesResponse])
async def get_modules_by_course(
    course_id: int = Query(..., description="ID of the course"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(100, ge=1, le=100, description="Items per page"),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get all modules for a specific course.

    **Query Parameters:**
    - `course_id`: ID of the course (required)
    - `page`: Page number (default: 1)
    - `per_page`: Items per page (default: 100, max: 100)

    **No authentication required** for public courses.
    """
    try:
        service = ModuleService(session)
        modules = await service.get_modules_by_course(
            course_id=course_id, page=page, per_page=per_page
        )

        modules_response = [ModuleResponse.model_validate(m) for m in modules]

        response_data = PaginatedModulesResponse(
            modules=modules_response,
            page=page,
            per_page=per_page,
            total=len(modules),
        )

        return success_response(
            data=response_data,
            details=f"Retrieved {len(modules)} module(s)",
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch modules: {str(e)}",
        )


@router.get("/{module_id}", response_model=ApiResponse[ModuleResponse])
async def get_module(
    module_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get a specific module by ID.

    **No authentication required** for public courses.
    """
    try:
        service = ModuleService(session)
        module = await service.get_module_by_id(module_id)

        if not module:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Module not found",
            )

        return success_response(
            data=module,
            details="Module retrieved successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch module: {str(e)}",
        )


@router.post("", response_model=ApiResponse[ModuleResponse])
async def create_module(
    module_data: ModuleCreate,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Create a new module.

    **Authentication required.**
    """
    try:
        service = ModuleService(session)
        module = await service.create_module(module_data.model_dump())

        return success_response(
            data=module,
            details="Module created successfully",
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create module: {str(e)}",
        )


@router.patch("/{module_id}", response_model=ApiResponse[ModuleResponse])
async def update_module(
    module_id: int,
    module_update: ModuleUpdate,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update a module.

    **Authentication required.**
    """
    try:
        service = ModuleService(session)
        updated_module = await service.update_module(
            module_id=module_id,
            module_update=module_update.model_dump(exclude_unset=True),
        )

        return success_response(
            data=updated_module,
            details="Module updated successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update module: {str(e)}",
        )


@router.delete("/{module_id}", response_model=ApiResponse[dict])
async def delete_module(
    module_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Delete a module.

    **Authentication required.**
    """
    try:
        service = ModuleService(session)
        await service.delete_module(module_id)

        return success_response(
            data={"module_id": module_id},
            details="Module deleted successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete module: {str(e)}",
        )


# UserModule Endpoints


@router.post("/start", response_model=ApiResponse[UserModuleResponse])
async def start_module(
    user_module_data: UserModuleCreate,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Start a module (create user module progress record).

    **Authentication required.**
    """
    try:
        assert current_user.id
        service = UserModuleService(session)
        user_module = await service.start_module(
            user_id=current_user.id,
            module_id=user_module_data.module_id,
            course_id=user_module_data.course_id,
        )

        return success_response(
            data=user_module,
            details="Module started successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start module: {str(e)}",
        )


@router.get("/user/modules", response_model=ApiResponse[PaginatedUserModulesResponse])
async def get_user_modules(
    course_id: int = Query(..., description="ID of the course"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get all user modules for a specific course.

    **Authentication required.**
    """
    try:
        assert current_user.id
        service = UserModuleService(session)
        user_modules = await service.get_user_modules_by_course(
            user_id=current_user.id,
            course_id=course_id,
        )

        user_modules_response = [
            UserModuleResponse.model_validate(um) for um in user_modules
        ]

        response_data = PaginatedUserModulesResponse(
            user_modules=user_modules_response,
            page=1,
            per_page=len(user_modules),
            total=len(user_modules),
        )

        return success_response(
            data=response_data,
            details=f"Retrieved {len(user_modules)} user module(s)",
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch user modules: {str(e)}",
        )


@router.get("/user/modules/detail", response_model=ApiResponse[UserModuleResponse])
async def get_user_module(
    module_id: int = Query(..., description="ID of the module"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get user module progress for a specific module.

    **Authentication required.**
    """
    try:
        assert current_user.id
        service = UserModuleService(session)
        user_module = await service.get_user_module(
            user_id=current_user.id,
            module_id=module_id,
        )

        return success_response(
            data=user_module,
            details="User module retrieved successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch user module: {str(e)}",
        )


@router.patch("/user/modules/update", response_model=ApiResponse[UserModuleResponse])
async def update_user_module(
    user_module_update: UserModuleUpdate,
    module_id: int = Query(..., description="ID of the module"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update user module progress.

    **Authentication required.**
    """
    try:
        assert current_user.id
        service = UserModuleService(session)

        update_data = (
            user_module_update.model_dump(exclude_unset=True)
            if user_module_update
            else {}
        )

        user_module = await service.update_user_module(
            user_id=current_user.id,
            module_id=module_id,
            update_data=update_data,
        )

        return success_response(
            data=user_module,
            details="User module updated successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user module: {str(e)}",
        )


@router.post("/user/modules/complete", response_model=ApiResponse[UserModuleResponse])
async def complete_module(
    module_id: int = Query(..., description="ID of the module"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Mark a module as completed.

    **Authentication required.**
    """
    try:
        assert current_user.id
        service = UserModuleService(session)
        user_module = await service.complete_module(
            user_id=current_user.id,
            module_id=module_id,
        )

        return success_response(
            data=user_module,
            details="Module completed successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete module: {str(e)}",
        )
