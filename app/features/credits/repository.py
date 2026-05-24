"""Credit ledger repository for database operations.

Provides a streamlined API with four core methods:
    - get: Retrieve a single ledger entry by flexible filters
    - get_many: Retrieve multiple entries with pagination, ordering, and filters
    - create: Append a new ledger entry
    - delete: Remove a ledger entry (admin use only)

Balance computation uses SQL SUM with TTL caching via cachetools
to avoid recalculating on every request.
"""

from typing import Optional
from cachetools import TTLCache
from sqlalchemy import func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, col
from .models import CreditLedger, CreditTransactionType


# Module-level TTL cache for credit balances.
# Key: user_id (int), Value: balance (int)
# TTL of 30 seconds balances freshness vs DB load.
_balance_cache: TTLCache[int, int] = TTLCache(maxsize=4096, ttl=30)


class CreditRepository:
    """Repository for credit ledger database operations.

    Uses a module-level TTL cache for balance lookups. The cache is
    automatically invalidated on create/delete operations for the
    affected user_id.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    # ==================== Balance ====================

    async def get_balance(self, user_id: int, *, use_cache: bool = True) -> int:
        """Get the current credit balance for a user.

        Balance is computed as COALESCE(SUM(amount), 0) over all ledger
        entries for the user. Results are cached with a 30-second TTL.

        Args:
            user_id: The user to query.
            use_cache: If False, bypasses the TTL cache and queries the DB directly.

        Returns:
            Current credit balance (can be zero, never negative if system is correct).
        """
        if use_cache and user_id in _balance_cache:
            return _balance_cache[user_id]

        result = await self.session.execute(
            select(func.coalesce(func.sum(CreditLedger.amount), 0)).where(
                col(CreditLedger.user_id) == user_id
            )
        )
        balance: int = result.scalar_one()
        _balance_cache[user_id] = balance
        return balance

    async def get_balance_for_update(self, user_id: int) -> int:
        """Get balance with a row-level lock for safe concurrent debits.

        Uses SELECT ... FOR UPDATE to prevent race conditions when
        multiple requests try to spend credits simultaneously.

        Args:
            user_id: The user to lock and query.

        Returns:
            Current credit balance under lock.
        """
        result = await self.session.execute(
            select(func.coalesce(func.sum(CreditLedger.amount), 0))
            .where(col(CreditLedger.user_id) == user_id)
            .with_for_update()
        )
        balance: int = result.scalar_one()
        return balance

    # ==================== Core CRUD ====================

    async def get(
        self,
        *,
        id: Optional[int] = None,
        user_id: Optional[int] = None,
        idempotency_key: Optional[str] = None,
        reference_id: Optional[str] = None,
        reference_type: Optional[str] = None,
        transaction_type: Optional[CreditTransactionType] = None,
    ) -> Optional[CreditLedger]:
        """Retrieve a single ledger entry matching the given filters.

        All filter arguments are optional and combined with AND logic.
        Returns the first match or None.

        Args:
            id: Primary key filter.
            user_id: Filter by user.
            idempotency_key: Filter by idempotency key.
            reference_id: Filter by reference ID.
            reference_type: Filter by reference type.
            transaction_type: Filter by transaction type.

        Returns:
            A single CreditLedger entry or None.
        """
        query = select(CreditLedger)

        if id is not None:
            query = query.where(col(CreditLedger.id) == id)
        if user_id is not None:
            query = query.where(col(CreditLedger.user_id) == user_id)
        if idempotency_key is not None:
            query = query.where(col(CreditLedger.idempotency_key) == idempotency_key)
        if reference_id is not None:
            query = query.where(col(CreditLedger.reference_id) == reference_id)
        if reference_type is not None:
            query = query.where(col(CreditLedger.reference_type) == reference_type)
        if transaction_type is not None:
            query = query.where(col(CreditLedger.transaction_type) == transaction_type)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_many(
        self,
        *,
        user_id: Optional[int] = None,
        transaction_type: Optional[CreditTransactionType] = None,
        reference_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[CreditLedger]:
        """Retrieve multiple ledger entries with pagination and filters.

        Results are ordered by created_at descending (newest first).

        Args:
            user_id: Filter by user.
            transaction_type: Filter by transaction type.
            reference_type: Filter by reference type.
            skip: Number of records to skip (for pagination).
            limit: Maximum number of records to return.

        Returns:
            List of CreditLedger entries matching the filters.
        """
        query = select(CreditLedger)

        if user_id is not None:
            query = query.where(col(CreditLedger.user_id) == user_id)
        if transaction_type is not None:
            query = query.where(col(CreditLedger.transaction_type) == transaction_type)
        if reference_type is not None:
            query = query.where(col(CreditLedger.reference_type) == reference_type)

        query = query.order_by(col(CreditLedger.created_at).desc())
        query = query.offset(skip).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count(
        self,
        *,
        user_id: Optional[int] = None,
        transaction_type: Optional[CreditTransactionType] = None,
        reference_type: Optional[str] = None,
    ) -> int:
        """Count ledger entries matching the given filters.

        Args:
            user_id: Filter by user.
            transaction_type: Filter by transaction type.
            reference_type: Filter by reference type.

        Returns:
            Number of matching entries.
        """
        query = select(func.count()).select_from(CreditLedger)

        if user_id is not None:
            query = query.where(col(CreditLedger.user_id) == user_id)
        if transaction_type is not None:
            query = query.where(col(CreditLedger.transaction_type) == transaction_type)
        if reference_type is not None:
            query = query.where(col(CreditLedger.reference_type) == reference_type)

        result = await self.session.execute(query)
        return result.scalar_one()

    async def create(self, entry: CreditLedger) -> CreditLedger:
        """Append a new ledger entry and invalidate the user's balance cache.

        The unique constraint on idempotency_key prevents duplicate transactions.

        Args:
            entry: The CreditLedger entry to insert.

        Returns:
            The created entry with its generated ID.

        Raises:
            IntegrityError: If the idempotency_key already exists.
        """
        self.session.add(entry)
        await self.session.flush()
        await self.session.refresh(entry)

        # Invalidate balance cache for this user
        _balance_cache.pop(entry.user_id, None)

        return entry

    async def delete(self, entry: CreditLedger) -> None:
        """Delete a ledger entry and invalidate the user's balance cache.

        This should only be used by admins for corrective actions.
        Normal operations should use refund entries instead.

        Args:
            entry: The CreditLedger entry to delete.
        """
        user_id = entry.user_id
        await self.session.delete(entry)
        await self.session.flush()

        # Invalidate balance cache for this user
        _balance_cache.pop(user_id, None)

    @staticmethod
    def invalidate_cache(user_id: int) -> None:
        """Manually invalidate the balance cache for a user.

        Useful when external operations modify the ledger outside
        the repository (e.g. bulk admin operations).

        Args:
            user_id: The user whose cache should be invalidated.
        """
        _balance_cache.pop(user_id, None)
