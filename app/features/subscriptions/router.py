"""Subscription API router."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import base64
import json
from app.common.deps import get_current_user, get_async_session
from app.features.users.models import User
from .models import Subscription
from .schemas import *
from .repository import SubscriptionRepository
from .google_play_service import GooglePlayService
from .service import SubscriptionService


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
    # Acknowledge immediately to avoid retries from Google
    # (FastAPI does this automatically by returning 200)

    try:
        # 3. Decode the Base64 data string
        decoded_data = base64.b64decode(payload.message.data).decode("utf-8")

        # 4. Parse the inner JSON into your original model
        notification_json = json.loads(decoded_data)
        play_data = GooglePlayNotification(**notification_json)

        # Now you can use play_data.subscriptionNotification safely
        print(f"Received event for: {play_data.packageName}")

    except Exception as e:
        print(f"Error decoding webhook: {e}")
        # Still return 200 so Google stops retrying if the data is malformed

    return {"status": "success"}
