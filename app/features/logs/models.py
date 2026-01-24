from datetime import datetime, timezone
from typing import Optional, Any, Dict
from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel
from app.common.events import LogLevel


class Log(SQLModel, table=True):
    __tablename__ = "logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    level: LogLevel = Field(default=LogLevel.INFO)
    message: str = Field(index=True)
    data: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
