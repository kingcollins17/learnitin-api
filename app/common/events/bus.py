import asyncio
import logging
import traceback
from typing import Callable, Dict, List, Any, Awaitable, Optional
from .schemas import Event

# Define a type for handlers: an async function that takes an Event
EventHandler = Callable[[Event], Awaitable[Any]]

logger = logging.getLogger(__name__)


class EventBus:
    """
    A simple in-memory async Event Bus for local Pub/Sub.
    """

    def __init__(self):
        self.queue: asyncio.Queue[Event] = asyncio.Queue()
        self.subscribers: Dict[str, List[EventHandler]] = {}
        self._is_running = False
        self._worker_task: Optional[asyncio.Task] = None

    def subscribe(self, event_type: str, handler: EventHandler):
        """Register a handler for a specific event type."""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(handler)
        handler_name = getattr(handler, "__name__", str(handler))
        logger.debug(f"Subscribed {handler_name} to {event_type}")

    async def publish(self, event: Event):
        """Publish an event to the queue."""
        await self.queue.put(event)
        logger.debug(f"Published event: {event.type}")

    async def _safe_handle(self, handler: EventHandler, event: Event):
        """Execute a handler safely, catching any exceptions."""
        try:
            await handler(event)
        except Exception as e:
            handler_name = getattr(handler, "__name__", str(handler))
            logger.error(
                f"Error in event handler {handler_name} for {event.type}: {str(e)}"
            )
            traceback.print_exc()

    async def _worker(self):
        """Background worker that processes events from the queue."""
        logger.info("Event Bus worker started")
        while self._is_running:
            try:
                event = await self.queue.get()
                handlers = self.subscribers.get(event.type, [])

                # Fan out to all subscribers
                for handler in handlers:
                    # Run each handler in its own task to avoid blocking the bus
                    asyncio.create_task(self._safe_handle(handler, event))

                self.queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in Event Bus worker loop: {str(e)}")
                await asyncio.sleep(1)  # Prevent tight loop on error

    def start(self):
        """Start the background worker."""
        if not self._is_running:
            self._is_running = True
            self._worker_task = asyncio.create_task(self._worker())

    async def stop(self):
        """Stop the background worker and wait for the queue to drain."""
        self._is_running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        logger.info("Event Bus worker stopped")


# Singleton instance
event_bus = EventBus()
