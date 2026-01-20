"""Google Play Developer API service."""

import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from app.common.config import settings


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
                credentials = service_account.Credentials.from_service_account_info(
                    service_account_info, scopes=self.scopes
                )
                self._service = build("androidpublisher", "v3", credentials=credentials)
            except Exception as e:
                # In a real app, log this properly
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
