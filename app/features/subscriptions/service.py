"""Subscription service for business logic."""

from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from .models import Subscription, SubscriptionStatus
from .repository import SubscriptionRepository
from .usage_repository import SubscriptionUsageRepository
from .google_play_service import GooglePlayService
from .schemas import SubscriptionVerifyRequest

# Dispatch notification event
from app.common.service import Commitable
from app.common.events import event_bus, NotificationInAppPushEvent, InAppEventType


from sqlalchemy.ext.asyncio import AsyncSession


class SubscriptionService(Commitable):
    """Service for managing subscriptions."""

    def __init__(
        self,
        subscription_repository: SubscriptionRepository,
        usage_repository: SubscriptionUsageRepository,
        google_play: GooglePlayService,
    ):
        self.subscription_repository = subscription_repository
        self.usage_repository = usage_repository
        self.google_play = google_play

    async def commit_all(self) -> None:
        """Commit all active sessions in the service's repositories."""
        await self.subscription_repository.session.commit()
        await self.usage_repository.session.commit()

    # ========== Private Helpers (DRY) ==========

    def _parse_google_response(self, google_resp: dict) -> Tuple[datetime, bool]:
        """Extract expiry time and auto_renew from Google Play response."""
        expiry_millis = int(google_resp.get("expiryTimeMillis", 0))
        expiry_date = datetime.fromtimestamp(
            expiry_millis / 1000, tz=timezone.utc
        ).replace(tzinfo=None)
        auto_renew = google_resp.get("autoRenewing", False) or False
        return expiry_date, auto_renew

    def _map_google_status(self, google_resp: dict) -> SubscriptionStatus:
        """Map Google Play response to internal status."""
        expiry_date, _ = self._parse_google_response(google_resp)

        if expiry_date < datetime.now(timezone.utc).replace(tzinfo=None):
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
        return await self.subscription_repository.get_by_purchase_token(purchase_token)

    async def _init_usage_tracking(self, subscription_id: int) -> None:
        """Initialize or refresh usage tracking for new period."""
        if self.usage_repository:
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            await self.usage_repository.get_or_create_for_subscription(
                subscription_id, now.year, now.month
            )

    async def _finalize_and_notify(
        self,
        sub: Subscription,
        title: str,
        message: str,
        is_new: bool = True,
        in_app_event: InAppEventType = InAppEventType.INFO,
    ) -> Subscription:
        """Shared logic for saving a subscription, tracking usage, and notifying user."""
        if is_new:
            sub = await self.subscription_repository.create(sub)
        else:
            sub = await self.subscription_repository.update(sub)

        if sub.id:
            await self._init_usage_tracking(sub.id)

        await event_bus.dispatch(
            NotificationInAppPushEvent(
                user_id=sub.user_id,
                title=title,
                message=message,
                type="subscription",
                in_app_event=in_app_event,
                data={"product_id": sub.product_id, "subscription_id": sub.id},
            )
        )
        return sub

    async def _update_status(
        self,
        purchase_token: str,
        status: SubscriptionStatus,
        auto_renew: Optional[bool] = None,
    ) -> Optional[Subscription]:
        """Simple status updates."""
        sub = await self._get_subscription_or_none(purchase_token)
        if not sub:
            return None

        sub.status = status
        if auto_renew is not None:
            sub.auto_renew = auto_renew
        return await self.subscription_repository.update(sub)

    # ========== Public API Methods ==========

    FREE_PRODUCT_ID = "free"

    def is_free_plan(self, subscription: Subscription) -> bool:
        """Check if a subscription is on the free plan."""
        return subscription.product_id == self.FREE_PRODUCT_ID

    async def get_active_subscription(self, user_id: int) -> Optional[Subscription]:
        """Get user's current valid subscription."""
        sub = await self.subscription_repository.get_active_by_user_id(user_id)
        if sub and sub.expiry_time > datetime.now(timezone.utc).replace(tzinfo=None):
            return sub
        return None

    async def create_free_subscription(self, user_id: int) -> Subscription:
        """Deactivate old plans and start a fresh free plan."""
        await self.subscription_repository.deactivate_all_for_user(user_id)
        expiry = (datetime.now(timezone.utc) + timedelta(days=30)).replace(tzinfo=None)

        sub = Subscription(
            user_id=user_id,
            product_id=self.FREE_PRODUCT_ID,
            purchase_token=None,
            status=SubscriptionStatus.ACTIVE,
            expiry_time=expiry,
            auto_renew=True,
        )
        return await self._finalize_and_notify(
            sub,
            title="Free Plan Activated",
            message="You're now on the Free plan. Ready to start your learning journey?",
            in_app_event=InAppEventType.INFO,
        )

    async def get_or_create_free_subscription(self, user_id: int) -> Subscription:
        """Ensure the user has at least some active plan."""
        existing = await self.get_active_subscription(user_id)
        return existing or await self.create_free_subscription(user_id)

    async def verify_and_save(
        self, user_id: int, request: SubscriptionVerifyRequest
    ) -> Subscription:
        """Handle client-side verification."""
        google_resp = await self.google_play.verify_subscription(
            request.product_id, request.purchase_token
        )
        expiry, auto_renew = self._parse_google_response(google_resp)
        status = self._map_google_status(google_resp)

        existing = await self._get_subscription_or_none(request.purchase_token)
        if existing:
            existing.user_id, existing.status = user_id, status
            existing.expiry_time, existing.auto_renew = expiry, auto_renew
            return await self._finalize_and_notify(
                existing,
                title="Subscription Activated",
                message="Success! Your premium status has been confirmed and updated.",
                is_new=False,
                in_app_event=InAppEventType.SUBSCRIPTION_PURCHASED,
            )

        await self.subscription_repository.deactivate_all_for_user(user_id)
        new_sub = Subscription(
            user_id=user_id,
            product_id=request.product_id,
            purchase_token=request.purchase_token,
            status=status,
            expiry_time=expiry,
            auto_renew=auto_renew,
        )
        return await self._finalize_and_notify(
            new_sub,
            title="Premium Activated!",
            message=f"Welcome to {request.product_id.replace('_', ' ').title()}! You've now unlocked all premium features.",
            in_app_event=InAppEventType.SUBSCRIPTION_PURCHASED,
        )

    async def sync_with_google(self, purchase_token: str) -> Optional[Subscription]:
        """On-demand sync without notifications."""
        sub = await self._get_subscription_or_none(purchase_token)
        if not sub or not sub.purchase_token:
            return sub

        google_resp = await self.google_play.verify_subscription(
            sub.product_id, sub.purchase_token
        )
        sub.expiry_time, sub.auto_renew = self._parse_google_response(google_resp)
        sub.status = SubscriptionStatus.ACTIVE
        return await self.subscription_repository.update(sub)

    # ========== Webhook Processing Methods ==========

    async def process_purchase(
        self, purchase_token: str, product_id: str, package_name: str
    ) -> Optional[Subscription]:
        """Webhook: Handle new subscription buy."""
        existing = await self._get_subscription_or_none(purchase_token)
        if not existing:
            return None  # Wait for verify_and_save

        google_resp = await self.google_play.verify_subscription(
            product_id, purchase_token
        )
        expiry, auto_renew = self._parse_google_response(google_resp)

        # Update if already active, otherwise treat as fresh buy
        if existing.status == SubscriptionStatus.ACTIVE:
            existing.expiry_time, existing.auto_renew = expiry, auto_renew
            existing.product_id = product_id
            return await self.subscription_repository.update(existing)

        await self.subscription_repository.deactivate_all_for_user(existing.user_id)
        new_sub = Subscription(
            user_id=existing.user_id,
            product_id=product_id,
            purchase_token=purchase_token,
            status=SubscriptionStatus.ACTIVE,
            expiry_time=expiry,
            auto_renew=auto_renew,
        )
        return await self._finalize_and_notify(
            new_sub,
            title="Premium Activated!",
            message=f"Your {product_id.replace('_', ' ').title()} access is now live. Enjoy your premium features!",
            in_app_event=InAppEventType.SUBSCRIPTION_PURCHASED,
        )

    async def process_renewal(self, purchase_token: str) -> Optional[Subscription]:
        """Webhook: Handle recurring charge."""
        existing = await self._get_subscription_or_none(purchase_token)
        if not existing or not existing.purchase_token:
            return None

        google_resp = await self.google_play.verify_subscription(
            existing.product_id, existing.purchase_token
        )
        expiry, auto_renew = self._parse_google_response(google_resp)

        await self.subscription_repository.deactivate_all_for_user(existing.user_id)
        new_sub = Subscription(
            user_id=existing.user_id,
            product_id=existing.product_id,
            purchase_token=purchase_token,
            status=SubscriptionStatus.ACTIVE,
            expiry_time=expiry,
            auto_renew=auto_renew,
        )
        return await self._finalize_and_notify(
            new_sub,
            title="Subscription Renewed",
            message=f"Your {existing.product_id.replace('_', ' ').title()} subscription has been successfully renewed.",
            in_app_event=InAppEventType.SUBSCRIPTION_PURCHASED,
        )

    async def process_cancellation(self, purchase_token: str) -> Optional[Subscription]:
        return await self._update_status(
            purchase_token, SubscriptionStatus.CANCELED, auto_renew=False
        )

    async def process_expiration(self, purchase_token: str) -> Optional[Subscription]:
        return await self._update_status(
            purchase_token, SubscriptionStatus.EXPIRED, auto_renew=False
        )

    async def process_pause(self, purchase_token: str) -> Optional[Subscription]:
        return await self._update_status(purchase_token, SubscriptionStatus.PAUSED)

    async def process_resume(self, purchase_token: str) -> Optional[Subscription]:
        """Sync details from Google when resuming."""
        sub = await self._get_subscription_or_none(purchase_token)
        return await self.sync_with_google(purchase_token) if sub else None

    async def process_revocation(self, purchase_token: str) -> Optional[Subscription]:
        return await self._update_status(
            purchase_token, SubscriptionStatus.EXPIRED, auto_renew=False
        )

    async def process_recovery(self, purchase_token: str) -> Optional[Subscription]:
        """Handle recovery from hold."""
        sub = await self._get_subscription_or_none(purchase_token)
        if not sub:
            return None
        sub = await self.sync_with_google(purchase_token)
        if sub:
            sub.auto_renew = True
            return await self.subscription_repository.update(sub)
        return None
