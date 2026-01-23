"""Google Play Developer API service."""

import json
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build
from app.common.config import settings


logger = logging.getLogger(__name__)


class GooglePlayService:
    """Service for interacting with Google Play Developer API."""

    def __init__(self):
        self.package_name = settings.GOOGLE_PLAY_PACKAGE_NAME
        self.scopes = ["https://www.googleapis.com/auth/androidpublisher"]
        self._service = None

    def _get_service(self):
        """Initialize and return the Google Play service."""
        if self._service is None:
            if not settings.FIREBASE_CREDENTIALS_JSON:
                raise ValueError("FIREBASE_CREDENTIALS_JSON is not configured")

            try:
                service_account_info = json.loads(settings.FIREBASE_CREDENTIALS_JSON)

                # Fix for incorrectly escaped newlines in private key from environment variables
                if "private_key" in service_account_info:
                    service_account_info["private_key"] = service_account_info[
                        "private_key"
                    ].replace("\\n", "\n")

                credentials = service_account.Credentials.from_service_account_info(
                    service_account_info, scopes=self.scopes
                )
                self._service = build("androidpublisher", "v3", credentials=credentials)
            except Exception as e:
                # In a real app, log this properly
                logger.error(f"Failed to initialize Google Play service: {e}")
                raise RuntimeError(
                    f"Failed to initialize Google Play service: {str(e)}"
                )

        return self._service

    async def verify_subscription(self, product_id: str, purchase_token: str):
        """
        Verify a subscription purchase with the Google Play Developer API.

        This method authenticates using the service account and retrieves
        the latest subscription details for the given product and token.

        Args:
            product_id: The identifier of the subscription product (e.g., 'premium_monthly').
            purchase_token: The token provided by the mobile application.

        Returns:
            A dictionary containing subscription details (expiryTimeMillis, autoRenewing, etc.).

        Raises:
            RuntimeError: If the API call fails or the service is not properly initialized.
        """
        if settings.GOOGLE_PLAY_MOCK:
            from datetime import datetime, timedelta, timezone

            logger.info(f"MOCK MODE: Verifying subscription {product_id}")
            # Success response simulation
            expiry_date = datetime.now(timezone.utc) + timedelta(days=30)
            return {
                "kind": "androidpublisher#subscriptionPurchase",
                "startTimeMillis": str(int(datetime.now().timestamp() * 1000)),
                "expiryTimeMillis": str(int(expiry_date.timestamp() * 1000)),
                "autoRenewing": True,
                "priceCurrencyCode": "USD",
                "priceAmountMicros": "9990000",
                "countryCode": "US",
                "paymentState": 1,  # 1 = Payment received
                "acknowledgementState": 1,
            }

        service = self._get_service()
        try:
            # Note: build() returns a sync client, but we can wrap it or just call it
            # For simplicity in this implementation, we use the sync call.
            # In high-load scenarios, consider offloading to a thread pool.
            request = (
                service.purchases()
                .subscriptions()
                .get(
                    packageName=self.package_name,
                    subscriptionId=product_id,
                    token=purchase_token,
                )
            )
            response = request.execute()
            return response
        except Exception as e:
            # Log error
            raise RuntimeError(f"Google Play API verification failed: {str(e)}")
