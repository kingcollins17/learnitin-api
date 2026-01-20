"""Subscription service for business logic."""

from datetime import datetime, timezone, timedelta
from typing import Optional
from .models import Subscription, SubscriptionStatus
from .repository import SubscriptionRepository
from .google_play_service import GooglePlayService
from .schemas import SubscriptionVerifyRequest


class SubscriptionService:
    """Service for managing subscriptions."""

    def __init__(
        self, repository: SubscriptionRepository, google_play: GooglePlayService
    ):
        self.repository = repository
        self.google_play = google_play

    def _map_google_status(self, google_resp: dict) -> SubscriptionStatus:
        """
        Map Google Play subscription response to internal status.

        Args:
            google_resp: The raw JSON response from the Google Play Developer API.

        Returns:
            The corresponding `SubscriptionStatus` enum.
        """
        # Simple mapping logic
        expiry_millis = int(google_resp.get("expiryTimeMillis", 0))
        expiry_date = datetime.fromtimestamp(expiry_millis / 1000, tz=timezone.utc)

        if expiry_date < datetime.now(timezone.utc):
            return SubscriptionStatus.EXPIRED

        # paymentState: 1 = Received, 2 = Free trial
        payment_state = google_resp.get("paymentState")
        if payment_state in [1, 2]:
            return SubscriptionStatus.ACTIVE

        return SubscriptionStatus.CANCELED  # Or PAUSED depending on other fields

    async def verify_and_save(
        self, user_id: int, request: SubscriptionVerifyRequest
    ) -> Subscription:
        """
        Verify purchase with Google Play and save/update in database.

        Args:
            user_id: The ID of the user who made the purchase.
            request: The verification request payload.

        Returns:
            The created or updated Subscription object.
        """
        google_resp = await self.google_play.verify_subscription(
            request.product_id, request.purchase_token
        )

        expiry_millis = int(google_resp.get("expiryTimeMillis", 0))
        expiry_date = datetime.fromtimestamp(expiry_millis / 1000, tz=timezone.utc)
        auto_renew = google_resp.get("autoRenewing", False)
        status = self._map_google_status(google_resp)

        # Check if subscription already exists
        existing = await self.repository.get_by_purchase_token(request.purchase_token)

        if existing:
            existing.status = status
            existing.expiry_time = expiry_date
            existing.auto_renew = auto_renew
            existing.user_id = user_id  # Ensure it belongs to the current user
            return await self.repository.update(existing)

        # Create new record
        new_sub = Subscription(
            user_id=user_id,
            product_id=request.product_id,
            purchase_token=request.purchase_token,
            status=status,
            expiry_time=expiry_date,
            auto_renew=auto_renew,
        )
        return await self.repository.create(new_sub)

    async def get_active_subscription(self, user_id: int) -> Optional[Subscription]:
        """
        Get the current active subscription for a user.

        Args:
            user_id: The ID of the user.

        Returns:
            The active `Subscription` if one exists and is not expired, else None.
        """
        sub = await self.repository.get_by_user_id(user_id)
        if (
            sub
            and sub.status == SubscriptionStatus.ACTIVE
            and sub.expiry_time > datetime.now(timezone.utc)
        ):
            return sub
        return None

    async def sync_with_google(self, purchase_token: str) -> Optional[Subscription]:
        """
        Resync subscription state from Google Play for a specific token.

        Args:
            purchase_token: The purchase token to sync.

        Returns:
            The updated `Subscription` object or None if not found in database.
        """
        sub = await self.repository.get_by_purchase_token(purchase_token)
        if not sub:
            return None

        google_resp = await self.google_play.verify_subscription(
            sub.product_id, sub.purchase_token
        )

        sub.status = self._map_google_status(google_resp)
        expiry_millis = int(google_resp.get("expiryTimeMillis", 0))
        sub.expiry_time = datetime.fromtimestamp(expiry_millis / 1000, tz=timezone.utc)
        sub.auto_renew = google_resp.get("autoRenewing", False)

        return await self.repository.update(sub)
