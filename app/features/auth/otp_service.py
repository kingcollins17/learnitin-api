import secrets
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.features.auth.otp_models import OTP
from app.features.auth.otp_repository import OTPRepository
from app.services.stytch_service import stytch_service


logger = logging.getLogger(__name__)


class OTPService:
    """Service for OTP operations."""

    def __init__(self, otp_repository: OTPRepository):
        self.otp_repository = otp_repository

    async def request_otp(
        self, email: Optional[str] = None, phone_number: Optional[str] = None
    ) -> OTP:
        """Generate and send an OTP."""
        if not email and not phone_number:
            raise ValueError("Either email or phone number must be provided")

        # Delete any existing unused OTPs for this recipient
        await self.otp_repository.delete_unused_otps(
            email=email,
            phone_number=phone_number,
        )

        # Create OTP record (code will be updated with method_id)
        otp = OTP(
            email=email,
            phone_number=phone_number,
            code="",  # Placeholder, will be replaced by Stytch method_id
            duration_minutes=10,
            created_at=datetime.now(timezone.utc),
        )

        # Call Stytch to send OTP
        method_id = ""
        if email:
            method_id = await stytch_service.send_email_otp(email)

        if not method_id and email:
            logger.error(f"Failed to send OTP via Stytch to {email}")
            # We continue but the record won't be very useful without a method_id

        # We store the method_id in the 'code' field so we can retrieve it for verification
        # The actual 6-digit code is handled by Stytch and not known to us.
        otp.code = method_id
        created_otp = await self.otp_repository.create(otp)

        return created_otp

    async def verify_otp(
        self, code: str, email: Optional[str] = None, phone_number: Optional[str] = None
    ) -> bool:
        """Verify an OTP using Stytch."""
        if email:
            # For Stytch, we need the method_id which we stored in the DB's 'code' field.
            # We look up the most recent valid OTP record for this email.
            # Using a simplified lookup:
            otp = await self.otp_repository.get_valid_otp_for_email(email)
            if not otp:
                return False

            # The 'code' argument passed to this function is the 6-digit code from the user.
            # The 'otp.code' in our DB is the Stytch method_id.
            is_valid = await stytch_service.verify_email_otp(otp.code, code)

            if is_valid:
                await self.otp_repository.mark_as_used(otp)
                return True
            return False

        return False

    async def cleanup_expired_otps(self) -> int:
        """Cleanup expired OTPs."""
        return await self.otp_repository.delete_expired_otps()

    async def verify_and_validate_otp_for_user(
        self, code: str, user_email: str
    ) -> bool:
        """
        Verify that an OTP code exists and belongs to the specified user using Stytch.
        """
        # Find the method_id from our database
        otp = await self.otp_repository.get_valid_otp_for_email(user_email)

        if not otp:
            raise ValueError("No valid OTP request found for this user")

        # Call Stytch for verification (code is the user input, otp.code is the method_id)
        is_valid = await stytch_service.verify_email_otp(otp.code, code)

        if not is_valid:
            raise ValueError("Invalid or expired OTP code")

        # Mark OTP as used
        await self.otp_repository.mark_as_used(otp)

        return True
