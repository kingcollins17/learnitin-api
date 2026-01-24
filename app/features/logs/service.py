from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from .repository import LogRepository
from .models import Log
from .schemas import LogCreate


class LogService:
    """Service for log business logic."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = LogRepository(session)

    async def create_log(self, log_data: LogCreate) -> Log:
        """Create a new log entry."""
        log = Log(
            level=log_data.level,
            message=log_data.message,
            data=log_data.data,
        )
        return await self.repository.create(log)

    async def get_log(self, log_id: int) -> Optional[Log]:
        """Get a log entry by ID."""
        return await self.repository.get_by_id(log_id)

    async def get_logs(self, skip: int = 0, limit: int = 100) -> List[Log]:
        """Get all log entries."""
        return await self.repository.get_all(skip, limit)

    async def delete_log(self, log_id: int) -> bool:
        """Delete a log entry."""
        log = await self.repository.get_by_id(log_id)
        if log:
            await self.repository.delete(log)
            return True
        return False

    async def clear_logs(self) -> None:
        """Clear all log entries."""
        await self.repository.delete_all()
