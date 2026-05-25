"""App Configurations API endpoints."""

import traceback
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.common.deps import get_active_admin, get_current_active_user
from app.common.dependencies import get_app_config_service
from app.common.events import LogEvent, LogLevel, event_bus
from app.common.responses import ApiResponse, success_response
from app.features.app_configs.schemas import (
    AppConfigCreate,
    AppConfigResponse,
    AppConfigUpdate,
)
from app.features.app_configs.service import AppConfigService
from app.features.users.models import User

router = APIRouter()


@router.post(
    "/",
    response_model=ApiResponse[AppConfigResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_app_config(
    config_data: AppConfigCreate,
    service: AppConfigService = Depends(get_app_config_service),
    admin: User = Depends(get_active_admin),
):
    """Create a new application configuration.

    **Admin only.**
    """
    try:
        config = await service.create_config(config_data.model_dump())
        await service.commit_all()

        return success_response(
            data=config,
            details="App configuration created successfully",
            status_code=status.HTTP_201_CREATED,
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        event_bus.dispatch(
            LogEvent(
                level=LogLevel.ERROR,
                message=f"Failed to create app config: {str(e)}",
                data={"error_trace": traceback.format_exc(), "key": config_data.key},
            )
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create app configuration: {str(e)}",
        )


@router.get("/", response_model=ApiResponse[List[AppConfigResponse]])
async def get_app_configs(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(100, ge=1, le=100, description="Items per page"),
    service: AppConfigService = Depends(get_app_config_service),
    current_user: User = Depends(get_current_active_user),
):
    """Get all application configurations with pagination.

    **All authenticated users.**
    """
    try:
        configs = await service.get_configs(page=page, per_page=per_page)
        return success_response(
            data=configs,
            details=f"Retrieved {len(configs)} app configurations",
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        event_bus.dispatch(
            LogEvent(
                level=LogLevel.ERROR,
                message=f"Failed to fetch app configs: {str(e)}",
                data={"error_trace": traceback.format_exc()},
            )
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch app configurations: {str(e)}",
        )


@router.get("/{key}", response_model=ApiResponse[AppConfigResponse])
async def get_app_config_by_key(
    key: str,
    service: AppConfigService = Depends(get_app_config_service),
    current_user: User = Depends(get_current_active_user),
):
    """Get a single application configuration by unique key.

    **All authenticated users.**
    """
    try:
        config = await service.get_config_by_key(key)
        return success_response(
            data=config,
            details=f"Retrieved configuration for key '{key}'",
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        event_bus.dispatch(
            LogEvent(
                level=LogLevel.ERROR,
                message=f"Failed to fetch app config key '{key}': {str(e)}",
                data={"error_trace": traceback.format_exc(), "key": key},
            )
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch app configuration: {str(e)}",
        )


@router.patch("/{config_id}", response_model=ApiResponse[AppConfigResponse])
async def update_app_config(
    config_id: int,
    config_update: AppConfigUpdate,
    service: AppConfigService = Depends(get_app_config_service),
    admin: User = Depends(get_active_admin),
):
    """Update an existing application configuration.

    **Admin only.**
    """
    try:
        updated = await service.update_config(
            config_id, config_update.model_dump(exclude_unset=True)
        )
        await service.commit_all()

        return success_response(
            data=updated,
            details="App configuration updated successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        event_bus.dispatch(
            LogEvent(
                level=LogLevel.ERROR,
                message=f"Failed to update app config id {config_id}: {str(e)}",
                data={"error_trace": traceback.format_exc(), "config_id": config_id},
            )
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update app configuration: {str(e)}",
        )


@router.delete("/{config_id}", response_model=ApiResponse[dict])
async def delete_app_config(
    config_id: int,
    service: AppConfigService = Depends(get_app_config_service),
    admin: User = Depends(get_active_admin),
):
    """Delete an application configuration.

    **Admin only.**
    """
    try:
        await service.delete_config(config_id)
        await service.commit_all()

        return success_response(
            data={"config_id": config_id},
            details="App configuration deleted successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        event_bus.dispatch(
            LogEvent(
                level=LogLevel.ERROR,
                message=f"Failed to delete app config id {config_id}: {str(e)}",
                data={"error_trace": traceback.format_exc(), "config_id": config_id},
            )
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete app configuration: {str(e)}",
        )
