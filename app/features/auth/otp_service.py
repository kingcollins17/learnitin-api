import secrets
import string
import logging
from datetime import datetime, timezone
from typing import Optional

from app.features.auth.otp_models import OTP
from app.features.auth.otp_repository import OTPRepository
from app.services.email_service import email_service


logger = logging.getLogger(__name__)


from sqlalchemy.ext.asyncio import AsyncSession


class OTPService:
    """Service for OTP operations."""

    def __init__(self, session: AsyncSession):
        self.otp_repository = OTPRepository(session)

    async def request_otp(self, email: str) -> OTP:
        """Generate and send an OTP code."""
        # Delete any existing unused OTPs for this recipient
        await self.otp_repository.delete_unused_otps(email=email)

        # Generate 6-digit code
        code = "".join(secrets.choice(string.digits) for _ in range(6))

        # Create OTP record
        otp = OTP(
            email=email,
            code=code,
            duration_minutes=10,
            created_at=datetime.now(timezone.utc),
        )

        created_otp = await self.otp_repository.create(otp)

        # Send email
        try:
            email_sent = email_service.send_email(
                to_email=email,
                subject="Your Verification Code",
                template_name="otp_verification.html",
                context={"code": code, "user_email": email, "duration_minutes": 10},
            )
            if not email_sent:
                logger.warning(
                    f"Failed to send OTP email to {email}. Code: {code} (Logged for dev)"
                )
            else:
                logger.info(f"OTP sent to {email}")
        except Exception as e:
            logger.error(f"Error sending OTP email: {e}")
            # In dev, we log the code so we can still proceed
            logger.warning(f"DEV: OTP code for {email} is {code}")

        return created_otp

    async def request_password_reset_otp(self, email: str) -> OTP:
        """Generate and send an OTP for password reset."""
        # Delete any existing unused OTPs for this recipient
        await self.otp_repository.delete_unused_otps(email=email)

        # Generate 6-digit code
        code = "".join(secrets.choice(string.digits) for _ in range(6))

        # Create OTP record
        otp = OTP(
            email=email,
            code=code,
            duration_minutes=10,
            created_at=datetime.now(timezone.utc),
        )

        created_otp = await self.otp_repository.create(otp)

        # Send email
        try:
            email_sent = email_service.send_email(
                to_email=email,
                subject="Reset Your Password",
                template_name="password_reset.html",
                context={"code": code, "user_email": email, "duration_minutes": 10},
            )
            if not email_sent:
                logger.warning(
                    f"Failed to send Password Reset OTP email to {email}. Code: {code}"
                )
            else:
                logger.info(f"Password Reset OTP sent to {email}")
        except Exception as e:
            logger.error(f"Error sending Password Reset OTP email: {e}")
            logger.warning(f"DEV: Reset code for {email} is {code}")

        return created_otp

    async def request_magic_link(self, email: str) -> OTP:
        """Generate and send an OTP via a Magic Link email."""
        # Delete any existing unused OTPs for this recipient
        await self.otp_repository.delete_unused_otps(email=email)

        # Generate 6-digit code
        code = "".join(secrets.choice(string.digits) for _ in range(6))

        # Create OTP record
        otp = OTP(
            email=email,
            code=code,
            duration_minutes=15,  # Give a bit more time for magic link
            created_at=datetime.now(timezone.utc),
        )

        created_otp = await self.otp_repository.create(otp)

        # Send email
        try:
            magic_link = f"https://www.learnitin.online/app/passwordless-signin?email={email}&otp={code}"

            email_sent = email_service.send_email(
                to_email=email,
                subject="Sign in to LearnItIn",
                template_name="magic_link.html",
                context={
                    "magic_link": magic_link,
                    "user_email": email,
                    "duration_minutes": 15,
                },
            )
            if not email_sent:
                logger.warning(
                    f"Failed to send Magic Link email to {email}. Link: {magic_link}"
                )
            else:
                logger.info(f"Magic Link sent to {email}")
        except Exception as e:
            logger.error(f"Error sending Magic Link email: {e}")
            logger.warning(f"DEV: Magic Link for {email} is {magic_link}")

        return created_otp

    async def verify_otp(self, code: str, email: str) -> bool:
        """Verify an OTP code (marks as used)."""
        otp = await self.otp_repository.get_valid_otp(code=code, email=email)

        if otp:
            await self.otp_repository.mark_as_used(otp)
            return True

        return False

    async def check_otp_validity(self, code: str, email: str) -> bool:
        """Check if an OTP code is valid without marking it as used."""
        otp = await self.otp_repository.get_valid_otp(code=code, email=email)
        return otp is not None

    async def cleanup_expired_otps(self) -> int:
        """Cleanup expired OTPs."""
        return await self.otp_repository.delete_expired_otps()

    async def verify_and_validate_otp_for_user(
        self, code: str, user_email: str
    ) -> bool:
        """
        Verify that an OTP code exists and belongs to the specified user.
        """
        otp = await self.otp_repository.get_valid_otp(code=code, email=user_email)

        if not otp:
            raise ValueError("Invalid or expired OTP code")

        # Mark OTP as used
        await self.otp_repository.mark_as_used(otp)

        return True
