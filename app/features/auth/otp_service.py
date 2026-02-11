import secrets
import string
import logging
from datetime import datetime, timezone
from typing import Optional, Literal

from app.features.auth.otp_models import OTP
from app.features.auth.otp_repository import OTPRepository
from app.services.email_service import EmailService


logger = logging.getLogger(__name__)

from app.common.service import Commitable


from sqlalchemy.ext.asyncio import AsyncSession


class OTPService(Commitable):
    """Service for OTP operations."""

    def __init__(self, repository: OTPRepository, email_service: EmailService):
        self.otp_repository = repository
        self.email_service = email_service

    async def commit_all(self) -> None:
        """Commit all active sessions in the service's repositories."""
        await self.otp_repository.session.commit()

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
            email_sent = self.email_service.send_email(
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

        await self.otp_repository.session.commit()
        return created_otp

    async def request_password_reset_otp(self, email: str) -> OTP:
        """Generate and send an OTP for password reset via Magic Link."""
        # Delete any existing unused OTPs for this recipient
        await self.otp_repository.delete_unused_otps(email=email)

        # Generate 6-digit code
        code = "".join(secrets.choice(string.digits) for _ in range(6))

        # Create OTP record
        otp = OTP(
            email=email,
            code=code,
            duration_minutes=15,  # Increased for magic link
            created_at=datetime.now(timezone.utc),
        )

        created_otp = await self.otp_repository.create(otp)

        # Send email
        try:
            magic_link = f"https://www.learnitin.online/app/reset-password?email={email}&otp={code}"

            email_sent = self.email_service.send_email(
                to_email=email,
                subject="Reset Your Password",
                template_name="magic_link_password_reset.html",
                context={
                    "magic_link": magic_link,
                    "user_email": email,
                    "duration_minutes": 15,
                },
            )
            if not email_sent:
                logger.warning(
                    f"Failed to send Password Reset email to {email}. Link: {magic_link}"
                )
            else:
                logger.info(f"Password Reset email sent to {email}")
        except Exception as e:
            logger.error(f"Error sending Password Reset email: {e}")
            logger.warning(f"DEV: Reset Link for {email} is {magic_link}")

        await self.otp_repository.session.commit()
        return created_otp

    async def request_magic_link(
        self,
        email: str,
        request_type: Literal["sign_in", "verification"] = "sign_in",
    ) -> OTP:
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
            # Different template and path based on request_type
            if request_type == "verification":
                path = "verify-account"
                subject = "Verify Your LearnItIn Account"
                template = "magic_link_verification.html"
            else:
                path = "passwordless-signin"
                subject = "Sign in to LearnItIn"
                template = "magic_link_signin.html"

            magic_link = (
                f"https://www.learnitin.online/app/{path}?email={email}&otp={code}"
            )

            email_sent = self.email_service.send_email(
                to_email=email,
                subject=subject,
                template_name=template,
                context={
                    "magic_link": magic_link,
                    "user_email": email,
                    "duration_minutes": 15,
                    "request_type": request_type,
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

        await self.otp_repository.session.commit()
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

        # Do not mark as used so it can be reused to sign-in (Improve user experience)
        # await self.otp_repository.mark_as_used(otp)

        return True
