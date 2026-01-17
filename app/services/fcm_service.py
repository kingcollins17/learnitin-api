"""Service for sending push notifications via Firebase Cloud Messaging."""

import os
import json
import logging
from typing import Optional, Dict, Any, List

import firebase_admin
from firebase_admin import credentials, messaging

from app.common.config import settings

logger = logging.getLogger(__name__)


class FirebaseFCMService:
    """Service for interacting with Firebase Cloud Messaging."""

    def __init__(self):
        self._initialize_app()

    def _initialize_app(self):
        """Initialize Firebase Admin SDK if not already initialized."""
        if not firebase_admin._apps:
            cred = None
            if settings.FIREBASE_CREDENTIALS_JSON:
                try:
                    # If it's a path to a file
                    if os.path.exists(settings.FIREBASE_CREDENTIALS_JSON):
                        cred = credentials.Certificate(
                            settings.FIREBASE_CREDENTIALS_JSON
                        )
                    else:
                        # Try parsing as JSON string
                        cred_info = json.loads(settings.FIREBASE_CREDENTIALS_JSON)
                        cred = credentials.Certificate(cred_info)
                except Exception as e:
                    logger.error(f"Error loading Firebase credentials: {e}")

            # If no explicit creds, let it try default (e.g. GCLOUD)
            if cred:
                firebase_admin.initialize_app(
                    cred, {"storageBucket": settings.FIREBASE_STORAGE_BUCKET}
                )
            else:
                # Fallback to default or assume already configured
                options = {}
                if settings.FIREBASE_STORAGE_BUCKET:
                    options["storageBucket"] = settings.FIREBASE_STORAGE_BUCKET

                try:
                    firebase_admin.initialize_app(options=options)
                except ValueError:
                    # App might be already initialized differently
                    pass

    def send_to_token(
        self,
        token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
        image_url: Optional[str] = None,
    ) -> Optional[str]:
        """
        Send a notification to a single device token.

        Args:
            token: The FCM registration token.
            title: Title of the notification.
            body: Body text of the notification.
            data: Additional key-value data to send with the notification.
            image_url: Optional URL of an image to display in the notification.

        Returns:
            The message ID if successful, None otherwise.
        """
        try:
            notification = messaging.Notification(
                title=title,
                body=body,
                image=image_url,
            )

            # Construct the message
            message = messaging.Message(
                notification=notification,
                data=data,
                token=token,
            )

            # Send the message
            response = messaging.send(message)
            logger.info(f"Successfully sent FCM message to token: {response}")
            return response
        except Exception as e:
            logger.error(f"Error sending FCM message to token {token}: {e}")
            return None

    def send_to_topic(
        self,
        topic: str,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
        image_url: Optional[str] = None,
    ) -> Optional[str]:
        """
        Send a notification to all devices subscribed to a topic.

        Args:
            topic: The name of the topic.
            title: Title of the notification.
            body: Body text of the notification.
            data: Additional key-value data to send.
            image_url: Optional image URL.

        Returns:
            The message ID if successful, None otherwise.
        """
        try:
            notification = messaging.Notification(
                title=title,
                body=body,
                image=image_url,
            )

            message = messaging.Message(
                notification=notification,
                data=data,
                topic=topic,
            )

            response = messaging.send(message)
            logger.info(f"Successfully sent FCM message to topic {topic}: {response}")
            return response
        except Exception as e:
            logger.error(f"Error sending FCM message to topic {topic}: {e}")
            return None

    def send_multicast(
        self,
        tokens: List[str],
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
        image_url: Optional[str] = None,
    ) -> Optional[messaging.BatchResponse]:
        """
        Send a notification to multiple device tokens.

        Args:
            tokens: List of FCM registration tokens.
            title: Title of the notification.
            body: Body text of the notification.
            data: Additional key-value data.
            image_url: Optional image URL.

        Returns:
            BatchResponse object containing results for each token.
        """
        if not tokens:
            return None

        try:
            notification = messaging.Notification(
                title=title,
                body=body,
                image=image_url,
            )

            message = messaging.MulticastMessage(
                notification=notification,
                data=data,
                tokens=tokens,
            )

            response = messaging.send_each_for_multicast(message)
            logger.info(
                f"Sent multicast FCM message. Success: {response.success_count}, Failure: {response.failure_count}"
            )
            return response
        except Exception as e:
            logger.error(f"Error sending multicast FCM message: {e}")
            return None


# Singleton instance
firebase_fcm_service = FirebaseFCMService()
