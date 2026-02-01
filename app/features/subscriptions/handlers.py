"""Event handlers for subscription webhook processing.

These handlers are thin wrappers that delegate to SubscriptionService.
They run in the background after the webhook endpoint returns 200.
"""

import logging

from app.common.database.session import AsyncSessionLocal
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
from .service import SubscriptionService

logger = logging.getLogger(__name__)


def _create_service(session) -> SubscriptionService:
    """Create a SubscriptionService with all dependencies."""
    return SubscriptionService(
        session=session,
        google_play=GooglePlayService(),
    )


async def handle_subscription_purchased(event: SubscriptionPurchasedEvent) -> None:
    """Handle new subscription purchase."""
    logger.info(
        f"Processing subscription purchase: token={event.purchase_token[:20]}..."
    )
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                service = _create_service(session)
                result = await service.process_purchase(
                    event.purchase_token, event.product_id, event.package_name
                )
                if result:
                    logger.info(f"Created subscription {result.id}")
                else:
                    logger.warning(
                        "Could not process purchase - no existing subscription found"
                    )
    except Exception as e:
        logger.error(f"Error processing subscription purchase: {e}")


async def handle_subscription_renewed(event: SubscriptionRenewedEvent) -> None:
    """Handle subscription renewal."""
    logger.info(
        f"Processing subscription renewal: token={event.purchase_token[:20]}..."
    )
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                service = _create_service(session)
                result = await service.process_renewal(event.purchase_token)
                if result:
                    logger.info(f"Renewed subscription {result.id}")
    except Exception as e:
        logger.error(f"Error processing subscription renewal: {e}")


async def handle_subscription_canceled(event: SubscriptionCanceledEvent) -> None:
    """Handle subscription cancellation."""
    logger.info(
        f"Processing subscription cancellation: token={event.purchase_token[:20]}..."
    )
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                service = _create_service(session)
                result = await service.process_cancellation(event.purchase_token)
                if result:
                    logger.info(f"Canceled subscription {result.id}")
    except Exception as e:
        logger.error(f"Error processing subscription cancellation: {e}")


async def handle_subscription_expired(event: SubscriptionExpiredEvent) -> None:
    """Handle subscription expiration."""
    logger.info(
        f"Processing subscription expiration: token={event.purchase_token[:20]}..."
    )
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                service = _create_service(session)
                result = await service.process_expiration(event.purchase_token)
                if result:
                    logger.info(f"Expired subscription {result.id}")
    except Exception as e:
        logger.error(f"Error processing subscription expiration: {e}")


async def handle_subscription_paused(event: SubscriptionPausedEvent) -> None:
    """Handle subscription pause."""
    logger.info(f"Processing subscription pause: token={event.purchase_token[:20]}...")
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                service = _create_service(session)
                result = await service.process_pause(event.purchase_token)
                if result:
                    logger.info(f"Paused subscription {result.id}")
    except Exception as e:
        logger.error(f"Error processing subscription pause: {e}")


async def handle_subscription_resumed(event: SubscriptionResumedEvent) -> None:
    """Handle subscription resume from pause."""
    logger.info(f"Processing subscription resume: token={event.purchase_token[:20]}...")
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                service = _create_service(session)
                result = await service.process_resume(event.purchase_token)
                if result:
                    logger.info(f"Resumed subscription {result.id}")
    except Exception as e:
        logger.error(f"Error processing subscription resume: {e}")


async def handle_subscription_revoked(event: SubscriptionRevokedEvent) -> None:
    """Handle subscription revocation (refund, chargeback)."""
    logger.info(
        f"Processing subscription revocation: token={event.purchase_token[:20]}..."
    )
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                service = _create_service(session)
                result = await service.process_revocation(event.purchase_token)
                if result:
                    logger.info(f"Revoked subscription {result.id}")
    except Exception as e:
        logger.error(f"Error processing subscription revocation: {e}")


async def handle_subscription_grace_period(event: SubscriptionGracePeriodEvent) -> None:
    """Handle subscription entering grace period due to payment issues."""
    logger.info(f"Processing grace period: token={event.purchase_token[:20]}...")
    # Keep subscription active during grace period, just log


async def handle_subscription_recovered(event: SubscriptionRecoveredEvent) -> None:
    """Handle subscription recovery from grace period/account hold."""
    logger.info(
        f"Processing subscription recovery: token={event.purchase_token[:20]}..."
    )
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                service = _create_service(session)
                result = await service.process_recovery(event.purchase_token)
                if result:
                    logger.info(f"Recovered subscription {result.id}")
    except Exception as e:
        logger.error(f"Error processing subscription recovery: {e}")
