"""Credit request/response schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from .models import CreditTransactionType


class CreditBalanceResponse(BaseModel):
    """Response schema for credit balance."""

    balance: int = Field(description="Current credit balance (sum of all ledger entries)")


class CreditLedgerEntryResponse(BaseModel):
    """Response schema for a single ledger entry."""

    id: int
    user_id: int
    amount: int
    transaction_type: CreditTransactionType
    description: Optional[str] = None
    reference_id: Optional[str] = None
    reference_type: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CreditHistoryResponse(BaseModel):
    """Paginated credit history response."""

    entries: list[CreditLedgerEntryResponse]
    total: int = Field(description="Total number of entries matching the filter")
    balance: int = Field(description="Current total balance")


class CreditPurchaseRequest(BaseModel):
    """Request schema for purchasing credits via Google Play."""

    product_id: str = Field(description="Google Play product ID for the credit pack")
    purchase_token: str = Field(description="Google Play purchase token (used as idempotency key)")
    amount: int = Field(gt=0, description="Number of credits to add")


class AdminCreditGrantRequest(BaseModel):
    """Request schema for admin granting credits to a user."""

    user_id: int = Field(description="Target user ID")
    amount: int = Field(description="Credits to grant (positive) or revoke (negative)")
    description: str = Field(
        min_length=1,
        description="Reason for the grant/revoke (required for audit trail)",
    )


class AdminCreditHistoryParams(BaseModel):
    """Query parameters for admin viewing a user's credit history."""

    user_id: int
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=200)
    transaction_type: Optional[CreditTransactionType] = None
