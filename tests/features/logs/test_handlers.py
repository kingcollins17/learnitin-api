import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.common.events import event_bus, LogEvent, LogLevel
from app.features.logs.models import Log
from app.features.logs.handlers import handle_log_event


@pytest.mark.asyncio
async def test_log_event_handler_direct(db_session: AsyncSession):
    """Test that handle_log_event correctly inserts a log into the database."""
    # 1. Create a log event
    event = LogEvent(
        level=LogLevel.WARNING,
        message="Test warning log message",
        data={"user_id": 42, "action": "test_action"},
    )

    # 2. Call the handler directly (which uses AsyncSessionLocal internally)
    await handle_log_event(event)

    # 3. Verify it was written to the database
    result = await db_session.execute(
        select(Log).where(Log.message == "Test warning log message")
    )
    logs = result.scalars().all()
    
    assert len(logs) == 1
    db_log = logs[0]
    assert db_log.level == LogLevel.WARNING
    assert db_log.message == "Test warning log message"
    assert db_log.data == {"user_id": 42, "action": "test_action"}


@pytest.mark.asyncio
async def test_log_event_handler_via_event_bus(db_session: AsyncSession):
    """Test that dispatching a LogEvent via the event bus invokes the handler and stores the log."""
    # 1. Dispatch the log event via the event bus
    event = LogEvent(
        level=LogLevel.ERROR,
        message="Critical system failure test",
        data={"service": "payment_service"},
    )
    
    # event_bus.dispatch is a normal method or async?
    # Let's check bus.py to see if it's async or sync, or wait for event bus processing.
    # Usually event_bus.dispatch is async or sync. In app/features/quiz/service.py: event_bus.dispatch(event) is called without await.
    # In app/features/subscriptions/service.py: await event_bus.dispatch(...) is called with await.
    # Let's support both or check what event_bus.dispatch signature is.
    import inspect
    from app.common.events.bus import event_bus
    
    if inspect.iscoroutinefunction(event_bus.dispatch):
        await event_bus.dispatch(event)
    else:
        event_bus.dispatch(event)

    # Wait a very brief moment if event processing is asynchronous background task, 
    # but event_bus might process synchronously in test or await is enough.
    # Let's fetch the log from the database
    result = await db_session.execute(
        select(Log).where(Log.message == "Critical system failure test")
    )
    logs = result.scalars().all()
    
    assert len(logs) == 1
    db_log = logs[0]
    assert db_log.level == LogLevel.ERROR
    assert db_log.message == "Critical system failure test"
    assert db_log.data == {"service": "payment_service"}
