from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, text
from sqlmodel import select, desc, delete
from app.features.auth.otp_models import OTP


class OTPRepository:
    """Repository for OTP database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def delete_unused_otps(
        self, email: Optional[str] = None, phone_number: Optional[str] = None
    ) -> None:
        """Delete unused OTPs for the given email or phone number."""
        # Start with base delete statement
        statement = delete(OTP).where(OTP.is_used == False)

        # Add specific conditions
        if email:
            statement = statement.where(OTP.email == email)
        if phone_number:
            statement = statement.where(OTP.phone_number == phone_number)

        # If neither provided, we shouldn't delete everything, but service guards that.
        if not email and not phone_number:
            return

        await self.session.execute(statement)
        await self.session.flush()

    async def delete_expired_otps(self) -> int:
        """Delete all expired OTPs."""
        # Clean implementation using raw SQL for MySQL date arithmetic
        # created_at + duration_minutes < now  => expired

        result = await self.session.execute(
            text(
                "DELETE FROM otps WHERE DATE_ADD(created_at, INTERVAL duration_minutes MINUTE) < NOW()"
            )
        )
        await self.session.flush()

        # safely get rowcount
        return getattr(result, "rowcount", 0)

    async def create(self, otp: OTP) -> OTP:
        """Create a new OTP."""
        self.session.add(otp)
        await self.session.flush()
        await self.session.refresh(otp)
        return otp

    async def get_valid_otp(
        self, code: str, email: Optional[str] = None, phone_number: Optional[str] = None
    ) -> Optional[OTP]:
        """Get a valid, unused OTP by code and email/phone."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        query = select(OTP).where(
            OTP.code == code,
            OTP.is_used == False,
            OTP.created_at >= now - timedelta(days=365),  # Simple valid check
        )

        if email:
            query = query.where(OTP.email == email)
        if phone_number:
            query = query.where(OTP.phone_number == phone_number)

        # Order by created_at desc to get the latest one if multiple exist (though ideally shouldn't be valid multiple)
        query = query.order_by(desc(OTP.created_at))

        result = await self.session.execute(query)
        return result.scalars().first()

    async def mark_as_used(self, otp: OTP) -> OTP:
        """Mark an OTP as used."""
        otp.is_used = True
        self.session.add(otp)
        await self.session.flush()
        await self.session.refresh(otp)
        return otp

    async def get_otp_by_code(self, code: str) -> Optional[OTP]:
        """Get OTP by code regardless of is_used status."""
        query = select(OTP).where(OTP.code == code).order_by(desc(OTP.created_at))
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_valid_otp_for_email(self, email: str) -> Optional[OTP]:
        """Get the latest unused OTP record for an email (contains Stytch method_id)."""
        query = (
            select(OTP)
            .where(OTP.email == email, OTP.is_used == False)
            .order_by(desc(OTP.created_at))
        )
        result = await self.session.execute(query)
        return result.scalars().first()
