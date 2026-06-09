"""Credit service for business logic.

Provides high-level operations for the credit system:
    - get_balance: Cached balance lookup
    - add_credits: Top up credits (purchase, bonus, admin grant, refund)
    - spend_credits: Debit credits with balance check and row-level locking
    - refund: Reverse a previous debit
    - get_history: Paginated transaction history

All debit operations hard-block on insufficient balance — no negative
balances are allowed.
"""

from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from app.common.service import Commitable
from .models import CreditLedger, CreditTransactionType
from .repository import CreditRepository


class InsufficientCreditsError(HTTPException):
    """Raised when a user tries to spend more credits than they have."""

    def __init__(self, balance: int, required: int):
        super().__init__(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "insufficient_credits",
                "balance": balance,
                "required": required,
                "message": f"Insufficient credits. You have {balance} credits but need {required}.",
            },
        )


class DuplicateTransactionError(HTTPException):
    """Raised when a transaction with the same idempotency key already exists."""

    def __init__(self, idempotency_key: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "duplicate_transaction",
                "idempotency_key": idempotency_key,
                "message": "This transaction has already been processed.",
            },
        )


class CreditService(Commitable):
    """Service for credit business logic.

    All credit movements flow through this service to ensure
    consistency, idempotency, and proper balance checks.
    """

    def __init__(self, repository: CreditRepository):
        self.repository = repository

    async def commit_all(self) -> None:
        """Commit all active sessions in the service's repositories."""
        await self.repository.session.commit()

    # ==================== Balance ====================

    async def get_balance(self, user_id: int) -> int:
        """Get current credit balance for a user.

        Uses the repository's TTL-cached balance to avoid
        recalculating on every call.

        Args:
            user_id: The user to query.

        Returns:
            Current credit balance.
        """
        return await self.repository.get_balance(user_id)

    # ==================== Credits (positive) ====================

    async def add_credits(
        self,
        user_id: int,
        amount: int,
        transaction_type: CreditTransactionType,
        description: str,
        *,
        reference_id: Optional[str] = None,
        reference_type: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> CreditLedger:
        """Add credits to a user's balance.

        Used for purchases, admin grants, bonuses, and refunds.
        The amount must be positive.

        Args:
            user_id: Target user.
            amount: Number of credits to add (must be > 0).
            transaction_type: The type of credit transaction.
            description: Human-readable description for audit trail.
            reference_id: Optional foreign key to related entity.
            reference_type: Optional type of the referenced entity.
            idempotency_key: Optional unique key to prevent duplicate transactions.

        Returns:
            The created ledger entry.

        Raises:
            HTTPException 400: If amount is not positive.
            DuplicateTransactionError: If idempotency_key already exists.
        """
        if amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Credit amount must be positive.",
            )

        # Check idempotency
        if idempotency_key:
            existing = await self.repository.get(idempotency_key=idempotency_key)
            if existing:
                raise DuplicateTransactionError(idempotency_key)

        entry = CreditLedger(
            user_id=user_id,
            amount=amount,
            transaction_type=transaction_type,
            description=description,
            reference_id=reference_id,
            reference_type=reference_type,
            idempotency_key=idempotency_key,
        )

        try:
            return await self.repository.create(entry)
        except IntegrityError:
            # Race condition: another request created the same idempotency key
            await self.repository.session.rollback()
            raise DuplicateTransactionError(idempotency_key or "unknown")

    # ==================== Debits (negative) ====================

    async def spend_credits(
        self,
        user_id: int,
        amount: int,
        transaction_type: CreditTransactionType,
        description: str,
        *,
        reference_id: Optional[str] = None,
        reference_type: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Optional[CreditLedger]:
        """Spend credits for an action. Hard-blocks on insufficient balance.

        Flow:
            1. Check idempotency key (if provided)
            2. Acquire row-level lock (SELECT FOR UPDATE)
            3. Check balance >= amount
            4. Insert negative ledger entry

        Args:
            user_id: The user spending credits.
            amount: Number of credits to spend (must be > 0, stored as negative).
            transaction_type: The type of debit transaction.
            description: Human-readable description for audit trail.
            reference_id: Optional foreign key to related entity.
            reference_type: Optional type of the referenced entity.
            idempotency_key: Optional unique key to prevent double-charges.

        Returns:
            The created ledger entry (with negative amount).

        Raises:
            HTTPException 400: If amount is not positive.
            InsufficientCreditsError: If balance < amount.
            DuplicateTransactionError: If idempotency_key already exists.
        """
        amount = abs(amount)
        if amount == 0:
            return None
        if amount < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Debit amount must be positive.",
            )

        # Check idempotency
        if idempotency_key:
            existing = await self.repository.get(idempotency_key=idempotency_key)
            if existing:
                raise DuplicateTransactionError(idempotency_key)

        # Acquire lock and check balance
        balance = await self.repository.get_balance_for_update(user_id)
        if balance < amount:
            raise InsufficientCreditsError(balance=balance, required=amount)

        entry = CreditLedger(
            user_id=user_id,
            amount=-amount,  # Stored as negative
            transaction_type=transaction_type,
            description=description,
            reference_id=reference_id,
            reference_type=reference_type,
            idempotency_key=idempotency_key,
        )

        try:
            return await self.repository.create(entry)
        except IntegrityError:
            await self.repository.session.rollback()
            raise DuplicateTransactionError(idempotency_key or "unknown")

    # ==================== Refund ====================

    async def refund(
        self,
        user_id: int,
        original_idempotency_key: str,
        description: str,
    ) -> CreditLedger:
        """Reverse a previous debit by inserting a positive refund entry.

        Looks up the original transaction by its idempotency key,
        validates it was a debit, then inserts a refund for the
        same absolute amount.

        Args:
            user_id: The user to refund.
            original_idempotency_key: The idempotency key of the original debit.
            description: Reason for the refund.

        Returns:
            The created refund ledger entry.

        Raises:
            HTTPException 404: If the original transaction is not found.
            HTTPException 400: If the original transaction is not a debit.
        """
        original = await self.repository.get(idempotency_key=original_idempotency_key)
        if not original:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Original transaction not found.",
            )

        if original.amount >= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only refund debit transactions (negative amount).",
            )

        refund_key = f"refund_{original_idempotency_key}"
        return await self.add_credits(
            user_id=user_id,
            amount=abs(original.amount),
            transaction_type=CreditTransactionType.REFUND,
            description=description,
            reference_id=original.reference_id,
            reference_type=original.reference_type,
            idempotency_key=refund_key,
        )

    # ==================== History ====================

    async def get_history(
        self,
        user_id: int,
        *,
        skip: int = 0,
        limit: int = 50,
        transaction_type: Optional[CreditTransactionType] = None,
    ) -> tuple[list[CreditLedger], int]:
        """Get paginated transaction history for a user.

        Args:
            user_id: The user to query.
            skip: Pagination offset.
            limit: Maximum entries to return.
            transaction_type: Optional filter by transaction type.

        Returns:
            Tuple of (entries, total_count).
        """
        entries = await self.repository.get_many(
            user_id=user_id,
            transaction_type=transaction_type,
            skip=skip,
            limit=limit,
        )
        total = await self.repository.count(
            user_id=user_id,
            transaction_type=transaction_type,
        )
        return entries, total
