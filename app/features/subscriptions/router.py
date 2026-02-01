"""Subscription API router."""

import base64
import json
import logging
import traceback

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import get_current_user, get_async_session
from app.common.events import LogEvent, LogLevel, event_bus
from app.common.responses import ApiResponse, success_response
from app.features.users.models import User
from .events import (
    SubscriptionPurchasedEvent,
    SubscriptionRenewedEvent,
    SubscriptionCanceledEvent,
    SubscriptionExpiredEvent,
    SubscriptionPausedEvent,
    SubscriptionResumedEvent,
    SubscriptionRevokedEvent,
    SubscriptionGracePeriodEvent,
    SubscriptionRecoveredEvent,
)
from .google_play_service import GooglePlayService
from .models import Subscription
from .repository import SubscriptionRepository
from .service import SubscriptionService
from .usage_service import SubscriptionUsageService
from .dependencies import (
    get_user_subscription,
    get_subscription_usage_service,
    get_subscription_service,
)
from .schemas import (
    PubSubPayload,
    SubscriptionNotificationType,
    SubscriptionResponse,
    SubscriptionVerifyRequest,
    GooglePlayNotification,
    SubscriptionUsageResponse,
)

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/subscriptions")


@router.get("/me", response_model=ApiResponse[SubscriptionResponse])
async def get_my_subscription(
    subscription: Subscription = Depends(get_user_subscription),
    usage_service: SubscriptionUsageService = Depends(get_subscription_usage_service),
):
    """
    Get the current user's active subscription with monthly usage.

    Automatically handles free plan creation/renewal if needed.
    """
    # Attach usage to subscription object for schema
    assert subscription.id is not None
    usage = await usage_service.get_usage(subscription.id)
    subscription_resp = SubscriptionResponse.model_validate(subscription)
    subscription_resp.usage = usage

    return success_response(
        data=subscription_resp, details="Subscription retrieved successfully"
    )


@router.post("/verify", response_model=ApiResponse[SubscriptionResponse])
async def verify_subscription(
    request: SubscriptionVerifyRequest,
    current_user: User = Depends(get_current_user),
    service: SubscriptionService = Depends(get_subscription_service),
    usage_service: SubscriptionUsageService = Depends(get_subscription_usage_service),
):
    """
    Verify a Google Play subscription and update user entitlement.
    """
    if current_user.id is None:
        raise HTTPException(status_code=401, detail="User ID not found")
    try:
        subscription = await service.verify_and_save(current_user.id, request)

        # Attach usage
        assert subscription.id is not None
        usage = await usage_service.get_usage(subscription.id)
        subscription_resp = SubscriptionResponse.model_validate(subscription)
        subscription_resp.usage = usage

        return success_response(
            data=subscription_resp, details="Subscription verified successfully"
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/resync", response_model=ApiResponse[SubscriptionResponse])
async def resync_subscription(
    purchase_token: str,
    current_user: User = Depends(get_current_user),
    service: SubscriptionService = Depends(get_subscription_service),
    usage_service: SubscriptionUsageService = Depends(get_subscription_usage_service),
):
    """
    Resync subscription status with Google Play.
    """
    subscription = await service.sync_with_google(purchase_token)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found"
        )

    # Attach usage
    assert subscription.id is not None
    usage = await usage_service.get_usage(subscription.id)
    subscription_resp = SubscriptionResponse.model_validate(subscription)
    subscription_resp.usage = usage

    return success_response(
        data=subscription_resp, details="Subscription resynced successfully"
    )


@router.post("/google/webhook", response_model=ApiResponse)
async def google_play_webhook(
    payload: PubSubPayload,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Handle Google Play Real-Time Developer Notifications (RTDN).

    This endpoint receives Pub/Sub messages from Google Play containing
    subscription state changes. It immediately returns 200 OK to acknowledge
    receipt, then dispatches events to be processed in the background.

    The bubus event bus handles async processing without blocking the response.
    """
    # Always return 200 to acknowledge receipt (prevents retries)
    # Process notification asynchronously via event bus

    try:
        if not payload.message or not payload.message.data:
            logger.warning("Received webhook with missing data")
            return success_response(
                data={"status": "success"}, details="Webhook received"
            )

        # Decode the Base64 data string
        decoded_data = base64.b64decode(payload.message.data).decode("utf-8")
        notification_json = json.loads(decoded_data)

        # Dispatch LogEvent with the decoded JSON data
        await event_bus.dispatch(
            LogEvent(
                level=LogLevel.INFO,
                message=f"Google Play Webhook Received: {notification_json.get('packageName', 'Unknown package')}",
                data=notification_json,
            )
        )

        play_data = GooglePlayNotification(**notification_json)

        logger.info(f"Received Google Play notification for: {play_data.packageName}")

        # Handle subscription notifications
        if play_data.subscriptionNotification:
            sub_notification = play_data.subscriptionNotification
            notification_type = sub_notification.notificationType
            purchase_token = sub_notification.purchaseToken or ""
            product_id = sub_notification.subscriptionId or ""
            package_name = play_data.packageName or ""

            # Check if subscription exists in our database
            # If not, return 404 to let Google retry later (client might not have verified yet)
            repo = SubscriptionRepository(session)
            existing = await repo.get_by_purchase_token(purchase_token)

            if not existing:
                logger.warning(
                    f"Subscription not found for token: {purchase_token[:20]}... Returning 404 for retry."
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Subscription not found, retry later",
                )

            # Dispatch appropriate event based on notification type
            if notification_type == SubscriptionNotificationType.SUBSCRIPTION_PURCHASED:
                await event_bus.dispatch(
                    SubscriptionPurchasedEvent(
                        purchase_token=purchase_token,
                        product_id=product_id,
                        package_name=package_name,
                    )
                )

            elif notification_type == SubscriptionNotificationType.SUBSCRIPTION_RENEWED:
                await event_bus.dispatch(
                    SubscriptionRenewedEvent(
                        purchase_token=purchase_token,
                        product_id=product_id,
                    )
                )

            elif (
                notification_type == SubscriptionNotificationType.SUBSCRIPTION_CANCELED
            ):
                await event_bus.dispatch(
                    SubscriptionCanceledEvent(purchase_token=purchase_token)
                )

            elif notification_type == SubscriptionNotificationType.SUBSCRIPTION_EXPIRED:
                await event_bus.dispatch(
                    SubscriptionExpiredEvent(purchase_token=purchase_token)
                )

            elif notification_type == SubscriptionNotificationType.SUBSCRIPTION_PAUSED:
                await event_bus.dispatch(
                    SubscriptionPausedEvent(purchase_token=purchase_token)
                )

            elif (
                notification_type == SubscriptionNotificationType.SUBSCRIPTION_RESTARTED
            ):
                await event_bus.dispatch(
                    SubscriptionResumedEvent(purchase_token=purchase_token)
                )

            elif notification_type == SubscriptionNotificationType.SUBSCRIPTION_REVOKED:
                await event_bus.dispatch(
                    SubscriptionRevokedEvent(purchase_token=purchase_token)
                )

            elif (
                notification_type
                == SubscriptionNotificationType.SUBSCRIPTION_IN_GRACE_PERIOD
            ):
                await event_bus.dispatch(
                    SubscriptionGracePeriodEvent(purchase_token=purchase_token)
                )

            elif (
                notification_type == SubscriptionNotificationType.SUBSCRIPTION_RECOVERED
            ):
                await event_bus.dispatch(
                    SubscriptionRecoveredEvent(purchase_token=purchase_token)
                )

            elif notification_type == SubscriptionNotificationType.SUBSCRIPTION_ON_HOLD:
                # Account hold - similar to grace period
                await event_bus.dispatch(
                    SubscriptionGracePeriodEvent(purchase_token=purchase_token)
                )

            else:
                logger.info(f"Unhandled notification type: {notification_type}")

        # Handle test notifications
        elif play_data.testNotification:
            logger.info(f"Received test notification: {play_data.testNotification}")

        # Handle one-time product notifications (not subscriptions)
        elif play_data.oneTimeProductNotification:
            logger.info("Received one-time product notification (not handling)")

    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        # Still return 200 to prevent Google from retrying malformed data

    return success_response(data={"status": "success"}, details="Webhook processed")
