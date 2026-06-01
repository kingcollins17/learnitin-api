"""Subscription API router."""

import base64
import json
import logging
import traceback

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import get_current_user, get_async_session
from app.common.events import LogEvent, LogLevel, event_bus
from app.common.config import settings
from app.common.responses import ApiResponse, success_response
from app.features.users.models import User
from app.features.credits.service import CreditService
from app.features.credits.models import CreditTransactionType
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
from app.common.dependencies import (
    get_subscription_repository,
    get_subscription_service,
    get_subscription_usage_service,
    get_credit_service,
)
from .dependencies import (
    get_user_subscription,
)
from .schemas import (
    PubSubPayload,
    SubscriptionNotificationType,
    SubscriptionResponse,
    SubscriptionVerifyRequest,
    GooglePlayNotification,
    SubscriptionUsageResponse,
    FreePlanLimitsResponse,
    PremiumPlanLimitsResponse,
)

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/subscriptions")


# --- Internal Helpers ---

async def _handle_credit_purchase(
    request: SubscriptionVerifyRequest,
    user_id: int,
    service: SubscriptionService,
    credit_service: CreditService,
) -> ApiResponse:
    amount = int(request.product_id.split('_')[0])
    
    google_resp = await service.google_play.verify_product(request.product_id, request.purchase_token)
    
    if google_resp.get("purchaseState") != 0:
         raise ValueError("Purchase is not verified or cancelled.")
    
    await credit_service.add_credits(
        user_id=user_id,
        amount=amount,
        transaction_type=CreditTransactionType.PURCHASE,
        description=f"Purchased {amount} credits",
        idempotency_key=request.purchase_token
    )
    await credit_service.commit_all()
    
    return success_response(
        data={"credits_added": amount, "product_id": request.product_id},
        details="Credits purchase verified successfully"
    )

async def _handle_subscription_purchase(
    request: SubscriptionVerifyRequest,
    user_id: int,
    service: SubscriptionService,
    credit_service: CreditService,
    usage_service: SubscriptionUsageService,
) -> ApiResponse:
    subscription = await service.verify_and_save(user_id, request)
    
    try:
        await credit_service.add_credits(
            user_id=user_id,
            amount=settings.PREMIUM_SUBSCRIPTION_CREDITS,
            transaction_type=CreditTransactionType.BONUS,
            description=f"Subscription bonus credits",
            idempotency_key=f"sub_bonus_{request.purchase_token}"
        )
        await credit_service.commit_all()
    except Exception as e:
        logger.warning(f"Failed to add subscription bonus credits: {e}")
        
    # Attach usage
    assert subscription.id is not None
    usage = await usage_service.get_usage(subscription.id)
    subscription_resp = SubscriptionResponse.model_validate(subscription)
    # subscription_resp.usage = usage

    return success_response(
        data=subscription_resp, details="Subscription verified successfully"
    )

async def _process_subscription_notification(
    sub_notification,
    package_name: str,
    repo: SubscriptionRepository
):
    notification_type = sub_notification.notificationType
    purchase_token = sub_notification.purchaseToken or ""
    product_id = sub_notification.subscriptionId or ""

    existing = await repo.get_by_purchase_token(purchase_token)

    if not existing:
        logger.warning(f"Subscription not found for token: {purchase_token[:20]}... Returning 404 for retry.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found, retry later")

    events = {
        SubscriptionNotificationType.SUBSCRIPTION_PURCHASED: SubscriptionPurchasedEvent(
            purchase_token=purchase_token, product_id=product_id, package_name=package_name
        ),
        SubscriptionNotificationType.SUBSCRIPTION_RENEWED: SubscriptionRenewedEvent(
            purchase_token=purchase_token, product_id=product_id
        ),
        SubscriptionNotificationType.SUBSCRIPTION_CANCELED: SubscriptionCanceledEvent(purchase_token=purchase_token),
        SubscriptionNotificationType.SUBSCRIPTION_EXPIRED: SubscriptionExpiredEvent(purchase_token=purchase_token),
        SubscriptionNotificationType.SUBSCRIPTION_PAUSED: SubscriptionPausedEvent(purchase_token=purchase_token),
        SubscriptionNotificationType.SUBSCRIPTION_RESTARTED: SubscriptionResumedEvent(purchase_token=purchase_token),
        SubscriptionNotificationType.SUBSCRIPTION_REVOKED: SubscriptionRevokedEvent(purchase_token=purchase_token),
        SubscriptionNotificationType.SUBSCRIPTION_IN_GRACE_PERIOD: SubscriptionGracePeriodEvent(purchase_token=purchase_token),
        SubscriptionNotificationType.SUBSCRIPTION_RECOVERED: SubscriptionRecoveredEvent(purchase_token=purchase_token),
        SubscriptionNotificationType.SUBSCRIPTION_ON_HOLD: SubscriptionGracePeriodEvent(purchase_token=purchase_token),
    }

    if notification_type in events:
        await event_bus.dispatch(events[notification_type])
    else:
        logger.info(f"Unhandled notification type: {notification_type}")

async def _process_one_time_product_notification(
    notification: dict,
    credit_service: CreditService,
    service: SubscriptionService
):
    notification_type = notification.get("notificationType")
    purchase_token = notification.get("purchaseToken")
    sku = notification.get("sku")
    
    logger.info(f"Received one-time product notification: {notification_type} for {sku}")
    
    if notification_type == 1 and sku and sku.endswith("_credits") and purchase_token:
        amount = int(sku.split('_')[0])
        try:
            existing = await credit_service.repository.get(idempotency_key=purchase_token)
            if existing:
                logger.info(f"Credit purchase {purchase_token} already processed.")
                return

            google_resp = await service.google_play.verify_product(sku, purchase_token)
            user_id_str = google_resp.get("obfuscatedExternalAccountId")
            purchase_state = google_resp.get("purchaseState")
            
            if purchase_state == 0 and user_id_str:
                user_id = int(user_id_str)
                await credit_service.add_credits(
                    user_id=user_id,
                    amount=amount,
                    transaction_type=CreditTransactionType.PURCHASE,
                    description=f"Purchased {amount} credits (webhook)",
                    idempotency_key=purchase_token
                )
                await credit_service.commit_all()
                logger.info(f"Added {amount} credits to user {user_id} via webhook.")
            else:
                logger.warning(f"Could not process webhook credit purchase. State: {purchase_state}, User: {user_id_str}")
        except Exception as ex:
            logger.error(f"Error processing credit purchase from webhook: {ex}")


@router.get("/me", response_model=ApiResponse[SubscriptionResponse])
async def get_my_subscription(
    subscription: Subscription = Depends(get_user_subscription),
    # usage_service: SubscriptionUsageService = Depends(get_subscription_usage_service),
):
    """
    Get the current user's active subscription with monthly usage.

    Automatically handles free plan creation/renewal if needed.
    """
    # Attach usage to subscription object for schema
    assert subscription.id is not None
    # usage = await usage_service.get_usage(subscription.id)
    subscription_resp = SubscriptionResponse.model_validate(subscription)
    # subscription_resp.usage = usage

    return success_response(
        data=subscription_resp, details="Subscription retrieved successfully"
    )


@router.get("/plans/free/limits", response_model=ApiResponse[FreePlanLimitsResponse])
async def get_free_plan_limits(
    service: SubscriptionService = Depends(get_subscription_service),
):
    """
    Get the monthly usage limits for the free plan.
    """
    limits = await service.get_free_plan_limits()
    return success_response(data=limits, details="Free plan limits retrieved")


@router.get("/plans/premium/limits", response_model=ApiResponse[PremiumPlanLimitsResponse])
async def get_premium_plan_limits():
    """
    Get the premium plan limits/entitlements. 
    ```{
  "status_code": 200,
  "details": "Premium plan limits retrieved",
  "data": {
    "bonus_credits": 800
  }
}```
    """
    limits = PremiumPlanLimitsResponse(bonus_credits=settings.PREMIUM_SUBSCRIPTION_CREDITS)
    return success_response(data=limits, details="Premium plan limits retrieved")


@router.post("/verify", response_model=ApiResponse)
async def verify_purchase(
    request: SubscriptionVerifyRequest,
    current_user: User = Depends(get_current_user),
    service: SubscriptionService = Depends(get_subscription_service),
    usage_service: SubscriptionUsageService = Depends(get_subscription_usage_service),
    credit_service: CreditService = Depends(get_credit_service),
):
    """
    Verify a Google Play purchase and update user entitlement or credits.
    """
    if current_user.id is None:
        raise HTTPException(status_code=401, detail="User ID not found")
    try:
        if request.product_id.endswith("_credits"):
            return await _handle_credit_purchase(request, current_user.id, service, credit_service)
        return await _handle_subscription_purchase(request, current_user.id, service, credit_service, usage_service)
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
    # subscription_resp.usage = usage

    return success_response(
        data=subscription_resp, details="Subscription resynced successfully"
    )


@router.post("/google/webhook", response_model=ApiResponse)
async def google_play_webhook(
    payload: PubSubPayload,
    repo: SubscriptionRepository = Depends(get_subscription_repository),
    credit_service: CreditService = Depends(get_credit_service),
    service: SubscriptionService = Depends(get_subscription_service),
):
    """
    Handle Google Play Real-Time Developer Notifications (RTDN).

    This endpoint receives Pub/Sub messages from Google Play containing
    subscription and one-time product state changes. It immediately returns 200 OK 
    to acknowledge receipt, then dispatches events to be processed in the background.

    The bubus event bus handles async processing without blocking the response.
    """
    # Always return 200 to acknowledge receipt (prevents retries)
    # Process notification asynchronously via event bus

    notification_json = {}
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
            await _process_subscription_notification(
                play_data.subscriptionNotification, play_data.packageName or "", repo
            )

        # Handle test notifications
        elif play_data.testNotification:
            logger.info(f"Received test notification: {play_data.testNotification}")

        # Handle one-time product notifications (not subscriptions)
        elif play_data.oneTimeProductNotification:
            await _process_one_time_product_notification(
                play_data.oneTimeProductNotification, credit_service, service
            )
                    
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        try:
            await event_bus.dispatch(
                LogEvent(
                    level=LogLevel.ERROR,
                    message=f"Error processing Google Play Webhook: {notification_json.get('packageName', 'Unknown package')}",
                    data={"error": str(e), "stacktrace": traceback.format_exc()},
                )
            )
        except:
            pass
        if isinstance(e, HTTPException):
            raise

        # Still return 200 to prevent Google from retrying malformed data

    return success_response(data={"status": "success"}, details="Webhook processed")
