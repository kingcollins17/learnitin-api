from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.database.session import get_async_session
from .service import LogService
from .schemas import LogRead
from app.common.responses import ApiResponse, success_response

router = APIRouter()


@router.get("/", response_model=ApiResponse[List[LogRead]])
async def get_logs(
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_async_session),
):
    """Get all logs."""
    service = LogService(session)
    logs = await service.get_logs(skip, limit)
    return success_response(data=logs, details=f"Retrieved {len(logs)} log(s)")


@router.get("/{log_id}", response_model=ApiResponse[LogRead])
async def get_log(
    log_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    """Get a log by ID."""
    service = LogService(session)
    log = await service.get_log(log_id)
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Log not found",
        )
    return success_response(data=log, details="Log retrieved successfully")


@router.delete("/{log_id}", response_model=ApiResponse)
async def delete_log(
    log_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    """Delete a log."""
    service = LogService(session)
    success = await service.delete_log(log_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Log not found",
        )
    return success_response(data={"log_id": log_id}, details="Log deleted successfully")


@router.delete("/", response_model=ApiResponse)
async def clear_logs(
    session: AsyncSession = Depends(get_async_session),
):
    """Clear all logs."""
    service = LogService(session)
    await service.clear_logs()
    return success_response(data={}, details="All logs cleared")
