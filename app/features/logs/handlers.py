import logging
from app.common.events import LogEvent
from app.common.database.session import AsyncSessionLocal
from .service import LogService
from .schemas import LogCreate

logger = logging.getLogger(__name__)


async def handle_log_event(event: LogEvent) -> None:
    """
    Handler for LogEvent.
    Logs the event into the database.
    """
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                service = LogService(session)
                log_data = LogCreate(
                    level=event.level,
                    message=event.message,
                    data=event.data,
                )
                await service.create_log(log_data)
    except Exception as e:
        logger.error(f"Error handling LogEvent: {e}")
