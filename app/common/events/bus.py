import logging
from bubus import EventBus

logger = logging.getLogger(__name__)

# Initialize the bubus EventBus
# We set max_history_size to 100 to keep a decent buffer of recent events
event_bus = EventBus(name="LearnItInBus", max_history_size=100)


async def start_bus():
    """No-op for bubus compatibility with existing start calls."""
    logger.info("bubus Event Bus active")


async def stop_bus():
    """Stop the bubus event bus."""
    await event_bus.stop(clear=True)
    logger.info("bubus Event Bus stopped")
