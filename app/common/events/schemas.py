from pydantic import BaseModel
from typing import Any, Dict, Optional
from datetime import datetime, timezone
from .types import EventType


class Event(BaseModel):
    """Base Event schema."""

    type: EventType
    payload: Dict[str, Any]
    timestamp: datetime = datetime.now(timezone.utc)
    metadata: Optional[Dict[str, Any]] = None
