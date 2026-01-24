"""Subscription API router."""

import base64
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import get_current_user, get_async_session
from app.common.events import LogEvent, LogLevel, event_bus
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
from .schemas import (
    PubSubPayload,
    SubscriptionNotificationType,
    SubscriptionResponse,
    SubscriptionVerifyRequest,
    GooglePlayNotification,
)
from .service import SubscriptionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/subscriptions")


async def get_subscription_service(
    session: AsyncSession = Depends(get_async_session),
) -> SubscriptionService:
    """Dependency to provide SubscriptionService."""
    repository = SubscriptionRepository(session)
    google_play = GooglePlayService()
    return SubscriptionService(repository, google_play)


@router.post("/verify", response_model=SubscriptionResponse)
async def verify_subscription(
    request: SubscriptionVerifyRequest,
    current_user: User = Depends(get_current_user),
    service: SubscriptionService = Depends(get_subscription_service),
):
    """
    Verify a Google Play subscription and update user entitlement.

    This endpoint should be called by the client after a successful purchase
    in the app. It verifies the purchase token with Google Play and
    updates the user's subscription record in the database.

    Args:
        request: The verification request containing product_id and purchase_token.
        current_user: The currently authenticated user.
        service: The subscription service instance.

    Returns:
        The updated or created subscription record.

    Raises:
        HTTPException: 400 if verification fails or 401 if user session is invalid.
    """
    if current_user.id is None:
        raise HTTPException(status_code=401, detail="User ID not found")
    try:
        subscription = await service.verify_and_save(current_user.id, request)

        return subscription
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/resync", response_model=SubscriptionResponse)
async def resync_subscription(
    purchase_token: str,
    current_user: User = Depends(get_current_user),
    service: SubscriptionService = Depends(get_subscription_service),
):
    """
    Resync subscription status with Google Play.

    Updates the local database record by re-verifying the provided token
    with the Google Play Developer API. Useful for recovery or restoring purchases.

    Args:
        purchase_token: The original purchase token to resync.
        current_user: The currently authenticated user.
        service: The subscription service instance.

    Returns:
        The updated subscription record.

    Raises:
        HTTPException: 404 if the subscription token is not found.
    """
    subscription = await service.sync_with_google(purchase_token)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found"
        )
    return subscription


@router.post("/google/webhook")
async def google_play_webhook(payload: PubSubPayload):
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
            return {"status": "success"}

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

            logger.info(f"Subscription notification type: {notification_type}")

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

    return {"status": "success"}
