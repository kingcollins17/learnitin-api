from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, col
from .models import Log
from app.common.events import LogLevel


class LogRepository:
    """Repository for log database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, log: Log) -> Log:
        """Create a new log entry."""
        self.session.add(log)
        await self.session.flush()
        await self.session.refresh(log)
        return log

    async def get_by_id(self, log_id: int) -> Optional[Log]:
        """Get a log entry by ID."""
        result = await self.session.execute(select(Log).where(Log.id == log_id))
        return result.scalar_one_or_none()

    async def get_all(
        self, skip: int = 0, limit: int = 100, level: Optional[LogLevel] = None
    ) -> List[Log]:
        """Get all log entries."""
        query = select(Log)
        if level:
            query = query.where(Log.level == level)
        
        result = await self.session.execute(
            query.order_by(col(Log.created_at).desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def delete(self, log: Log) -> None:
        """Delete a log entry."""
        await self.session.delete(log)
        await self.session.flush()

    async def delete_all(self) -> None:
        """Delete all log entries."""
        result = await self.session.execute(select(Log))
        logs = result.scalars().all()
        for log in logs:
            await self.session.delete(log)
        await self.session.flush()

