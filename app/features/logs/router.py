from typing import List, Optional
import traceback
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.database.session import get_async_session
from .service import LogService
from .schemas import LogRead
from app.common.responses import ApiResponse, success_response
from app.common.events import LogEvent, LogLevel, event_bus
from app.common.deps import get_current_active_user
from app.features.users.models import User

router = APIRouter()


async def __get_current_admin_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Require the current user to be a superuser (admin)."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


@router.get("/", response_model=ApiResponse[List[LogRead]])
async def get_logs(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    level: Optional[LogLevel] = Query(None, description="Filter logs by level"),
    session: AsyncSession = Depends(get_async_session),
    admin: User = Depends(__get_current_admin_user),
):
    """Get all logs."""
    try:
        skip = (page - 1) * per_page
        service = LogService(session)
        logs = await service.get_logs(skip=skip, limit=per_page, level=level)
        return success_response(data=logs, details=f"Retrieved {len(logs)} log(s)")
    except Exception as e:
        traceback.print_exc()
        error_msg = f"Failed to fetch logs: {str(e)}"
        await event_bus.dispatch(
            LogEvent(
                level=LogLevel.ERROR,
                message=error_msg,
                data={
                    "endpoint": "get_logs",
                    "page": page,
                    "per_page": per_page,
                    "level": level,
                    "error": str(e),
                    "stacktrace": traceback.format_exc(),
                },
            )
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg,
        )



@router.get("/{log_id}", response_model=ApiResponse[LogRead])
async def get_log(
    log_id: int,
    session: AsyncSession = Depends(get_async_session),
    admin: User = Depends(__get_current_admin_user),
):
    """Get a log by ID."""
    try:
        service = LogService(session)
        log = await service.get_log(log_id)
        if not log:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Log not found",
            )
        return success_response(data=log, details="Log retrieved successfully")
    except HTTPException as e:
        await event_bus.dispatch(
            LogEvent(
                level=LogLevel.ERROR,
                message=f"HTTPException in get_log: {e.detail}",
                data={
                    "endpoint": "get_log",
                    "log_id": log_id,
                    "status_code": e.status_code,
                    "detail": e.detail,
                },
            )
        )
        raise
    except Exception as e:
        traceback.print_exc()
        error_msg = f"Failed to fetch log details: {str(e)}"
        await event_bus.dispatch(
            LogEvent(
                level=LogLevel.ERROR,
                message=error_msg,
                data={
                    "endpoint": "get_log",
                    "log_id": log_id,
                    "error": str(e),
                    "stacktrace": traceback.format_exc(),
                },
            )
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg,
        )


@router.delete("/{log_id}", response_model=ApiResponse)
async def delete_log(
    log_id: int,
    session: AsyncSession = Depends(get_async_session),
    admin: User = Depends(__get_current_admin_user),
):
    """Delete a log."""
    try:
        service = LogService(session)
        success = await service.delete_log(log_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Log not found",
            )
        return success_response(
            data={"log_id": log_id}, details="Log deleted successfully"
        )
    except HTTPException as e:
        await event_bus.dispatch(
            LogEvent(
                level=LogLevel.ERROR,
                message=f"HTTPException in delete_log: {e.detail}",
                data={
                    "endpoint": "delete_log",
                    "log_id": log_id,
                    "status_code": e.status_code,
                    "detail": e.detail,
                },
            )
        )
        raise
    except Exception as e:
        traceback.print_exc()
        error_msg = f"Failed to delete log: {str(e)}"
        await event_bus.dispatch(
            LogEvent(
                level=LogLevel.ERROR,
                message=error_msg,
                data={
                    "endpoint": "delete_log",
                    "log_id": log_id,
                    "error": str(e),
                    "stacktrace": traceback.format_exc(),
                },
            )
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg,
        )


@router.delete("/", response_model=ApiResponse)
async def clear_logs(
    session: AsyncSession = Depends(get_async_session),
    admin: User = Depends(__get_current_admin_user),
):
    """Clear all logs."""
    try:
        service = LogService(session)
        await service.clear_logs()
        return success_response(data={}, details="All logs cleared")
    except Exception as e:
        traceback.print_exc()
        error_msg = f"Failed to clear logs: {str(e)}"
        await event_bus.dispatch(
            LogEvent(
                level=LogLevel.ERROR,
                message=error_msg,
                data={
                    "endpoint": "clear_logs",
                    "error": str(e),
                    "stacktrace": traceback.format_exc(),
                },
            )
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg,
        )
