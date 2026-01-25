"""Stytch service for authentication and OTPs."""

import logging
from typing import Optional
import stytch
from app.common.config import settings

logger = logging.getLogger(__name__)


class StytchService:
    """Service to handle Stytch operations."""

    def __init__(self):
        self._client: Optional[stytch.Client] = None

    @property
    def client(self) -> stytch.Client:
        if self._client is None:
            if settings.STYTCH_PROJECT_ID and settings.STYTCH_SECRET:
                self._client = stytch.Client(
                    project_id=settings.STYTCH_PROJECT_ID,
                    secret=settings.STYTCH_SECRET,
                    environment=settings.STYTCH_ENVIRONMENT,
                )
            else:
                raise RuntimeError("Stytch credentials not configured")
        return self._client

    async def send_email_otp(self, email: str) -> str:
        """
        Send an OTP code to an email address using Stytch.
        Returns the method_id required for authentication.
        """
        try:
            # Stytch SDK supports async calls via .async_
            # Note: Depending on the version, it might be client.otps.email.login_or_create
            # For OTPs, login_or_create is common.
            response = await self.client.otps.email.login_or_create_async(email=email)
            if response.status_code == 200:
                return response.email_id
            else:
                logger.error(f"Stytch failed to send OTP: {response}")
                return ""
        except Exception as e:
            logger.error(f"Failed to send Stytch email OTP: {e}")
            return ""

    async def verify_email_otp(self, method_id: str, code: str) -> bool:
        """
        Verify an OTP code using Stytch.
        """
        try:
            response = await self.client.otps.authenticate_async(
                method_id=method_id,
                code=code,
                session_duration_minutes=60,  # Optional session creation
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to verify Stytch email OTP: {e}")
            return False


# Singleton instance
stytch_service = StytchService()
