from datetime import datetime
from typing import Optional, Any, Dict
from pydantic import BaseModel
from app.common.events import LogLevel


class LogBase(BaseModel):
    level: LogLevel = LogLevel.INFO
    message: str
    data: Optional[Dict[str, Any]] = None


class LogCreate(LogBase):
    pass


class LogRead(LogBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
