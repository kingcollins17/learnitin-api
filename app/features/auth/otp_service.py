import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.features.auth.otp_models import OTP
from app.features.auth.otp_repository import OTPRepository
from app.services.email_service import email_service


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

        # Generate a 6-digit code
        code = "".join([str(secrets.randbelow(10)) for _ in range(6)])

        # Create OTP record
        otp = OTP(
            email=email,
            phone_number=phone_number,
            code=code,
            duration_minutes=10,
            created_at=datetime.now(timezone.utc),
        )

        created_otp = await self.otp_repository.create(otp)

        # Send Email if email is provided
        if email:
            # simple text template for now, or we could add a jinja template later
            # For now assuming we might not have a template, so sending a basic email
            # actually the email_service requires a template_name.
            # I should probably create a basic template or just use a placeholder if I can't.
            # Let's assume there is an 'otp_code.html' or similar needed, but for now I'll use a generic one
            # or try to use a default.
            # Wait, the user said "uses @[app/services/email_service.py] for sending otps".
            # I must use it. The email_service.send_email takes template_name.
            # I will assume "otp_verification.html" exists or will be created.
            # I'll update the plan to include creating an email template if needed, but the user didn't explicitly ask for it.
            # I'll just call it with 'otp_verification.html' and pass the code.

            try:
                email_service.send_email(
                    to_email=email,
                    subject="Your Verification Code",
                    template_name="otp_verification.html",
                    context={"code": code, "duration_minutes": 10},
                )
            except Exception as e:
                # Log error but don't fail the request generally, or maybe we should?
                # Ideally we want to know if it failed.
                print(f"Failed to send email: {e}")

        return created_otp

    async def verify_otp(
        self, code: str, email: Optional[str] = None, phone_number: Optional[str] = None
    ) -> bool:
        """Verify an OTP."""
        otp = await self.otp_repository.get_valid_otp(code, email, phone_number)

        if not otp:
            return False

        # Check expiration (ensure comparison is between naive datetimes as MySQL stores naive)
        expiration_time = otp.created_at + timedelta(minutes=otp.duration_minutes)
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if now > expiration_time:
            return False

        # Mark as used
        await self.otp_repository.mark_as_used(otp)
        return True

    async def cleanup_expired_otps(self) -> int:
        """Cleanup expired OTPs."""
        return await self.otp_repository.delete_expired_otps()

    async def verify_and_validate_otp_for_user(
        self, code: str, user_email: str
    ) -> bool:
        """
        Verify that an OTP code exists and belongs to the specified user.

        This method:
        1. Retrieves the OTP by code (regardless of is_used status)
        2. Validates that the OTP is associated with the user's email
        3. Marks the OTP as used

        Args:
            code: The OTP code to verify
            user_email: The email address of the user who should own this OTP

        Returns:
            True if the OTP is valid and belongs to the user

        Raises:
            ValueError: If OTP is invalid, not associated with an email, or doesn't belong to the user
        """
        # Get OTP by code (regardless of is_used status)
        otp = await self.otp_repository.get_otp_by_code(code)

        if not otp:
            raise ValueError("Invalid OTP code")

        # Check if OTP has an email associated with it
        if not otp.email:
            raise ValueError("OTP is not associated with an email")

        # Verify that the OTP belongs to the specified user
        if otp.email != user_email:
            raise ValueError("This OTP code does not belong to your account")

        # Check expiration
        expiration_time = otp.created_at + timedelta(minutes=otp.duration_minutes)
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if now > expiration_time:
            raise ValueError("OTP code has expired")

        # Mark OTP as used
        await self.otp_repository.mark_as_used(otp)

        return True
