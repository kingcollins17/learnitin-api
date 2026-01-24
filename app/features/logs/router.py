from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.database.session import get_async_session
from .service import LogService
from .schemas import LogRead

router = APIRouter()


@router.get("/", response_model=List[LogRead])
async def get_logs(
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_async_session),
):
    """Get all logs."""
    service = LogService(session)
    return await service.get_logs(skip, limit)


@router.get("/{log_id}", response_model=LogRead)
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
    return log


@router.delete("/{log_id}")
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
    return {"message": "Log deleted"}


@router.delete("/")
async def clear_logs(
    session: AsyncSession = Depends(get_async_session),
):
    """Clear all logs."""
    service = LogService(session)
    await service.clear_logs()
    return {"message": "All logs cleared"}
