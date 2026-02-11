"""Review database models."""

from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING
from sqlmodel import Field, SQLModel, Relationship, Column
from sqlalchemy import Text, ForeignKey, Integer, UniqueConstraint

if TYPE_CHECKING:
    from app.features.users.models import User
    from app.features.courses.models import Course


class Review(SQLModel, table=True):
    """Review model for database."""

    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("user_id", "course_id", name="uq_review_user_course"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    course_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("courses.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    rating: int = Field(ge=1, le=5, nullable=False)
    comment: Optional[str] = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(default=None)

    # Relationships
    user: Optional["User"] = Relationship()
    course: Optional["Course"] = Relationship()

    class Config:
        """Pydantic config."""

        from_attributes = True
