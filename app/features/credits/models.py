"""Credit ledger database models.

Implements append-only ledger accounting where:
- Every credit movement is an immutable row
- Balance = SUM(amount) WHERE user_id = ?
- Positive amount = credit (purchase, grant, bonus, refund)
- Negative amount = debit (course gen, lesson unlock, audio gen, quiz gen)
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from sqlmodel import Field, SQLModel, Column
from sqlalchemy import ForeignKey, Integer, Index, Text


class CreditTransactionType(str, Enum):
    """Types of credit transactions.

    Credit (positive amount):
        PURCHASE - User bought credits via Google Play
        ADMIN_GRANT - Admin manually granted credits
        BONUS - Promotional or referral bonus
        REFUND - Reversal of a failed/refunded action
        WELCOME - New user welcome credits

    Debit (negative amount):
        COURSE_GENERATION - Generated a learning journey
        LESSON_UNLOCK - Unlocked a lesson
        AUDIO_GENERATION - Generated audio for a lesson
        QUIZ_GENERATION - Generated a quiz
    """

    # Credits (positive)
    PURCHASE = "purchase"
    ADMIN_GRANT = "admin_grant"
    BONUS = "bonus"
    REFUND = "refund"
    WELCOME = "welcome"

    # Debits (negative)
    COURSE_GENERATION = "course_generation"
    LESSON_UNLOCK = "lesson_unlock"
    AUDIO_GENERATION = "audio_generation"
    QUIZ_GENERATION = "quiz_generation"


class CreditLedger(SQLModel, table=True):
    """Append-only credit ledger entry.

    Each row represents a single credit movement. The user's balance
    is never stored directly — it is always computed as:
        SELECT COALESCE(SUM(amount), 0) FROM credit_ledger WHERE user_id = ?

    Attributes:
        amount: Signed integer. Positive for credits, negative for debits.
        idempotency_key: Unique key to prevent duplicate transactions
            (e.g. Google Play purchase_token for purchases).
        reference_id: Foreign key to the entity this transaction relates to
            (e.g. course_id, lesson_id). Stored as string for flexibility.
        reference_type: Type of the referenced entity (e.g. "course", "lesson").
    """

    __tablename__ = "credit_ledger"
    __table_args__ = (
        Index("ix_credit_ledger_user_created", "user_id", "created_at"),
        Index("ix_credit_ledger_user_type", "user_id", "transaction_type"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    amount: int = Field(nullable=False)
    transaction_type: CreditTransactionType = Field(nullable=False, index=True)
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    reference_id: Optional[str] = Field(default=None, max_length=255, index=True)
    reference_type: Optional[str] = Field(default=None, max_length=50)
    idempotency_key: Optional[str] = Field(
        default=None, max_length=255, unique=True, index=True
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        """Pydantic config."""

        from_attributes = True
