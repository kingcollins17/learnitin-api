"""SQLModel base configuration."""
from sqlmodel import SQLModel

# This is the base class for all SQLModel models
# All models should inherit from SQLModel with table=True
__all__ = ["SQLModel"]
