"""Subscription service for business logic."""

from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from .models import Subscription, SubscriptionStatus, SubscriptionUsage
from .repository import SubscriptionRepository
from .usage_repository import SubscriptionUsageRepository
from .google_play_service import GooglePlayService
from .schemas import SubscriptionVerifyRequest

# Dispatch notification event
from app.common.events import event_bus, NotificationInAppPushEvent


class SubscriptionService:
    """Service for managing subscriptions."""

    def __init__(
        self,
        repository: SubscriptionRepository,
        google_play: GooglePlayService,
        usage_repository: Optional[SubscriptionUsageRepository] = None,
    ):
        self.repository = repository
        self.google_play = google_play
        self.usage_repository = usage_repository

    # ========== Private Helpers (DRY) ==========

    def _parse_google_response(self, google_resp: dict) -> Tuple[datetime, bool]:
        """Extract expiry time and auto_renew from Google Play response."""
        expiry_millis = int(google_resp.get("expiryTimeMillis", 0))
        expiry_date = datetime.fromtimestamp(expiry_millis / 1000, tz=timezone.utc)
        auto_renew = google_resp.get("autoRenewing", False) or False
        return expiry_date, auto_renew

    def _map_google_status(self, google_resp: dict) -> SubscriptionStatus:
        """Map Google Play response to internal status."""
        expiry_date, _ = self._parse_google_response(google_resp)

        if expiry_date < datetime.now(timezone.utc):
            return SubscriptionStatus.EXPIRED

        # paymentState: 1 = Received, 2 = Free trial
        payment_state = google_resp.get("paymentState")
        if payment_state in [1, 2]:
            return SubscriptionStatus.ACTIVE

        return SubscriptionStatus.CANCELED

    async def _get_subscription_or_none(
        self, purchase_token: str
    ) -> Optional[Subscription]:
        """Get subscription by token or return None."""
        return await self.repository.get_by_purchase_token(purchase_token)

    async def _verify_and_update_from_google(self, sub: Subscription) -> Subscription:
        """Re-verify with Google and update subscription fields."""
        google_resp = await self.google_play.verify_subscription(
            sub.product_id, sub.purchase_token
        )
        expiry_date, auto_renew = self._parse_google_response(google_resp)

        sub.expiry_time = expiry_date
        sub.status = SubscriptionStatus.ACTIVE
        sub.auto_renew = auto_renew
        return sub

    async def _update_status(
        self,
        purchase_token: str,
        status: SubscriptionStatus,
        auto_renew: Optional[bool] = None,
    ) -> Optional[Subscription]:
        """Update subscription status (common pattern for simple status changes)."""
        sub = await self._get_subscription_or_none(purchase_token)
        if not sub:
            return None

        sub.status = status
        if auto_renew is not None:
            sub.auto_renew = auto_renew
        return await self.repository.update(sub)

    async def _init_usage_tracking(self, subscription_id: int) -> None:
        """Initialize or refresh usage tracking for new period."""
        if self.usage_repository:
            now = datetime.now(timezone.utc)
            await self.usage_repository.get_or_create_for_subscription(
                subscription_id, now.year, now.month
            )

    # ========== Public API Methods ==========

    # Free plan product ID (not associated with Google Play)
    FREE_PRODUCT_ID = "free"

    async def get_active_subscription(self, user_id: int) -> Optional[Subscription]:
        """
        Get user's active subscription if one exists.

        Args:
            user_id: The ID of the user.

        Returns:
            The active Subscription or None if not found.
        """
        return await self.repository.get_active_by_user_id(user_id)

    async def create_free_subscription(self, user_id: int) -> Subscription:
        """
        Create a new free plan subscription for user.

        Always creates a new subscription - does not check for existing ones.
        Use get_or_create_free_subscription if you want to avoid duplicates.

        Args:
            user_id: The ID of the user.

        Returns:
            The newly created free plan Subscription.
        """
        now = datetime.now(timezone.utc)
        one_month_later = now + timedelta(days=30)

        # deactivate all previous active subscriptions
        await self.repository.deactivate_all_for_user(user_id)

        free_sub = Subscription(
            user_id=user_id,
            product_id=self.FREE_PRODUCT_ID,
            purchase_token=None,
            status=SubscriptionStatus.ACTIVE,
            expiry_time=one_month_later,
            auto_renew=True,
        )
        free_sub = await self.repository.create(free_sub)

        if free_sub.id:
            await self._init_usage_tracking(free_sub.id)

        await event_bus.dispatch(
            NotificationInAppPushEvent(
                user_id=user_id,
                title="Welcome to LearnItIn!",
                message="Your free plan is now active. Enjoy learning!",
                type="subscription",
                data={
                    "product_id": self.FREE_PRODUCT_ID,
                    "subscription_id": free_sub.id,
                },
            )
        )

        return free_sub

    async def get_or_create_free_subscription(self, user_id: int) -> Subscription:
        """
        Get existing active subscription or create a free plan for user.

        Args:
            user_id: The ID of the user.

        Returns:
            The user's active subscription or a newly created free plan.
        """
        existing = await self.get_active_subscription(user_id)
        if existing:
            return existing

        return await self.create_free_subscription(user_id)

    def is_free_plan(self, subscription: Subscription) -> bool:
        """Check if subscription is a free plan."""
        return subscription.product_id == self.FREE_PRODUCT_ID

    async def verify_and_save(
        self, user_id: int, request: SubscriptionVerifyRequest
    ) -> Subscription:
        """Verify purchase with Google Play and save/update in database."""
        google_resp = await self.google_play.verify_subscription(
            request.product_id, request.purchase_token
        )
        print(f"Google response={google_resp}")

        expiry_date, auto_renew = self._parse_google_response(google_resp)
        status = self._map_google_status(google_resp)

        existing = await self._get_subscription_or_none(request.purchase_token)

        if existing:
            existing.status = status
            existing.expiry_time = expiry_date
            existing.auto_renew = auto_renew
            existing.user_id = user_id
            return await self.repository.update(existing)

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
        """Get current active subscription for a user."""
        sub = await self.repository.get_by_user_id(user_id)
        if (
            sub
            and sub.status == SubscriptionStatus.ACTIVE
            and sub.expiry_time > datetime.now(timezone.utc)
        ):
            return sub
        return None

    async def sync_with_google(self, purchase_token: str) -> Optional[Subscription]:
        """Resync subscription state from Google Play."""
        sub = await self._get_subscription_or_none(purchase_token)
        if not sub:
            return None

        sub = await self._verify_and_update_from_google(sub)
        return await self.repository.update(sub)

    # ========== Webhook Processing Methods ==========

    async def process_purchase(
        self, purchase_token: str, product_id: str, package_name: str
    ) -> Optional[Subscription]:
        """Process new subscription purchase - deactivate old, create new."""
        google_resp = await self.google_play.verify_subscription(
            product_id, purchase_token
        )
        expiry_date, auto_renew = self._parse_google_response(google_resp)

        existing = await self._get_subscription_or_none(purchase_token)
        if not existing:
            return None

        user_id = existing.user_id
        await self.repository.deactivate_all_for_user(user_id)

        new_sub = Subscription(
            user_id=user_id,
            product_id=product_id,
            purchase_token=purchase_token,
            status=SubscriptionStatus.ACTIVE,
            expiry_time=expiry_date,
            auto_renew=auto_renew,
        )
        new_sub = await self.repository.create(new_sub)

        if new_sub.id:
            await self._init_usage_tracking(new_sub.id)

        # Dispatch notification event
        await event_bus.dispatch(
            NotificationInAppPushEvent(
                user_id=user_id,
                title="Subscription Activated!",
                message=f"Your {product_id} subscription is now active.",
                type="subscription",
                data={"product_id": product_id, "subscription_id": new_sub.id},
            )
        )

        return new_sub

    async def process_renewal(self, purchase_token: str) -> Optional[Subscription]:
        """Process subscription renewal - deactivate old and create new subscription."""
        existing = await self._get_subscription_or_none(purchase_token)
        if not existing:
            return None

        # Verify with Google Play to get new expiry
        google_resp = await self.google_play.verify_subscription(
            existing.product_id, existing.purchase_token  # type: ignore
        )
        expiry_date, auto_renew = self._parse_google_response(google_resp)

        user_id = existing.user_id
        product_id = existing.product_id

        # Deactivate all old subscriptions and create new one
        await self.repository.deactivate_all_for_user(user_id)

        new_sub = Subscription(
            user_id=user_id,
            product_id=product_id,
            purchase_token=purchase_token,
            status=SubscriptionStatus.ACTIVE,
            expiry_time=expiry_date,
            auto_renew=auto_renew,
        )
        new_sub = await self.repository.create(new_sub)

        if new_sub.id:
            await self._init_usage_tracking(new_sub.id)

        # Dispatch notification event
        await event_bus.dispatch(
            NotificationInAppPushEvent(
                user_id=user_id,
                title="Subscription Renewed!",
                message=f"Your {product_id} subscription has been renewed.",
                type="subscription",
                data={"product_id": product_id, "subscription_id": new_sub.id},
            )
        )

        return new_sub

    async def process_cancellation(self, purchase_token: str) -> Optional[Subscription]:
        """Process cancellation - mark canceled but keep active until expiry."""
        return await self._update_status(
            purchase_token, SubscriptionStatus.CANCELED, auto_renew=False
        )

    async def process_expiration(self, purchase_token: str) -> Optional[Subscription]:
        """Process expiration."""
        return await self._update_status(
            purchase_token, SubscriptionStatus.EXPIRED, auto_renew=False
        )

    async def process_pause(self, purchase_token: str) -> Optional[Subscription]:
        """Process subscription pause."""
        return await self._update_status(purchase_token, SubscriptionStatus.PAUSED)

    async def process_resume(self, purchase_token: str) -> Optional[Subscription]:
        """Process subscription resume from pause."""
        sub = await self._get_subscription_or_none(purchase_token)
        if not sub:
            return None

        sub = await self._verify_and_update_from_google(sub)
        return await self.repository.update(sub)

    async def process_revocation(self, purchase_token: str) -> Optional[Subscription]:
        """Process revocation (refund/chargeback)."""
        return await self._update_status(
            purchase_token, SubscriptionStatus.EXPIRED, auto_renew=False
        )

    async def process_recovery(self, purchase_token: str) -> Optional[Subscription]:
        """Process recovery from grace period/account hold."""
        sub = await self._get_subscription_or_none(purchase_token)
        if not sub:
            return None

        sub = await self._verify_and_update_from_google(sub)
        sub.auto_renew = True  # Recovered subscriptions default to auto-renew
        return await self.repository.update(sub)
