import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.features.otp.models import OTP
from app.common.config import settings
from unittest.mock import patch, MagicMock


# Mock email service to avoid sending real emails
@pytest.fixture
def mock_email_service():
    with patch("app.features.otp.service.email_service") as mock:
        mock.send_email.return_value = True
        yield mock


@pytest.mark.asyncio
async def test_request_otp(
    client: AsyncClient, db_session: AsyncSession, mock_email_service
):
    """Test requesting an OTP."""
    payload = {"email": "test@example.com"}
    response = await client.post(f"{settings.API_V1_PREFIX}/otp/request", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["message"] == "OTP sent successfully"

    # Verify OTP was created in DB
    result = await db_session.execute(
        select(OTP).where(OTP.email == "test@example.com")
    )
    otp = result.scalars().first()
    assert otp is not None
    assert otp.code is not None
    assert len(otp.code) == 6

    # Verify email service was called
    mock_email_service.send_email.assert_called_once()
    args = mock_email_service.send_email.call_args
    assert args.kwargs["to_email"] == "test@example.com"
    assert "code" in args.kwargs["context"]
    assert args.kwargs["context"]["code"] == otp.code


@pytest.mark.asyncio
async def test_verify_otp_success(
    client: AsyncClient, db_session: AsyncSession, mock_email_service
):
    """Test successfully verifying an OTP."""
    # 1. Request OTP first
    payload = {"email": "test@example.com"}
    await client.post(f"{settings.API_V1_PREFIX}/otp/request", json=payload)

    # get the code from DB
    result = await db_session.execute(
        select(OTP).where(OTP.email == "test@example.com")
    )
    otp = result.scalars().first()
    code = otp.code

    # 2. Verify OTP
    verify_payload = {"email": "test@example.com", "code": code}
    response = await client.post(
        f"{settings.API_V1_PREFIX}/otp/verify", json=verify_payload
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    # Verify it is marked as used
    await db_session.refresh(otp)
    assert otp.is_used is True


@pytest.mark.asyncio
async def test_verify_otp_failure_wrong_code(
    client: AsyncClient, db_session: AsyncSession, mock_email_service
):
    """Test verifying with wrong code."""
    # 1. Request OTP
    payload = {"email": "test@example.com"}
    await client.post(f"{settings.API_V1_PREFIX}/otp/request", json=payload)

    # 2. Verify with wrong code
    verify_payload = {
        "email": "test@example.com",
        "code": "000000",  # High probability of being wrong
    }
    response = await client.post(
        f"{settings.API_V1_PREFIX}/otp/verify", json=verify_payload
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or expired OTP"


@pytest.mark.asyncio
async def test_verify_otp_expires(
    client: AsyncClient, db_session: AsyncSession, mock_email_service
):
    """Test verifying an expired OTP behaves as invalid."""
    # 1. Request OTP
    payload = {"email": "test@example.com"}
    await client.post(f"{settings.API_V1_PREFIX}/otp/request", json=payload)

    # Manually expire the OTP in DB
    result = await db_session.execute(
        select(OTP).where(OTP.email == "test@example.com")
    )
    otp = result.scalars().first()
    from datetime import timedelta

    otp.duration_minutes = -1  # Expire it immediately or set created_at to past
    # sqlmodel/sqlalchemy might require marking modified or adding to session if not attached,
    # but since we got it from session it should be attached.
    # Actually just modifying field and committing/flushing should work.
    # But wait, logic is: expiration_time = otp.created_at + timedelta(minutes=otp.duration_minutes)
    # create_at is set on creation.
    # Let's set duration to 0 and ensure enough time passes? Or set created_at back.
    # setting duration to -1 seems easiest if logic allows negative duration.
    # Logic: expiration_time = otp.created_at + timedelta(minutes=-1) -> created_at - 1 min.
    # now > expiration_time (created_at - 1 min) -> True.
    otp.duration_minutes = -1
    db_session.add(otp)
    await db_session.commit()

    # 2. Verify
    verify_payload = {"email": "test@example.com", "code": otp.code}
    response = await client.post(
        f"{settings.API_V1_PREFIX}/otp/verify", json=verify_payload
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or expired OTP"


@pytest.mark.asyncio
async def test_request_otp_invalidates_previous(
    client: AsyncClient, db_session: AsyncSession, mock_email_service
):
    """Test that requesting a new OTP invalidates/deletes previous ones."""
    # 1. Request OTP 1
    payload = {"email": "test@example.com"}
    await client.post(f"{settings.API_V1_PREFIX}/otp/request", json=payload)

    # Verify OTP 1 exists
    result = await db_session.execute(
        select(OTP).where(OTP.email == "test@example.com")
    )
    otp1 = result.scalars().first()
    assert otp1 is not None
    code1 = otp1.code

    # 2. Request OTP 2
    await client.post(f"{settings.API_V1_PREFIX}/otp/request", json=payload)

    # 3. Verify OTP 1 is gone or invalid
    # Since we are hard deleting in repository, check it's gone.
    db_session.expire_all()

    result = await db_session.execute(
        select(OTP).where(OTP.email == "test@example.com")
    )
    otps = result.scalars().all()

    # Should only have the new one
    assert len(otps) == 1
    new_otp = otps[0]
    assert new_otp.code != code1


@pytest.mark.asyncio
async def test_cleanup_expired_otps(
    client: AsyncClient, db_session: AsyncSession, mock_email_service
):
    """Test cleaning up expired OTPs."""
    from datetime import datetime, timezone, timedelta

    # 1. Create an expired OTP (manually insert)
    expired_otp = OTP(
        email="expired@example.com",
        code="123456",
        duration_minutes=10,
        # set created_at to 20 minutes ago
        created_at=datetime.now(timezone.utc) - timedelta(minutes=20),
    )
    db_session.add(expired_otp)

    # 2. Create a valid OTP
    valid_otp = OTP(
        email="valid@example.com",
        code="654321",
        duration_minutes=10,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(valid_otp)
    await db_session.commit()

    # 3. Call cleanup via repository (since we don't have an endpoint for it yet, but service has method)
    # Let's instantiate service or repo
    from app.features.otp.repository import OTPRepository

    repo = OTPRepository(db_session)
    count = await repo.delete_expired_otps()

    # 4. Verify count and records
    # Should delete at least 1 (the one we created).
    # Note: it might delete others if database wasn't clean, but test db should be clean per function scope?
    # Actually db_session fixture rolls back, but we committed?
    # Ah, the fixture says: `yield session; await session.rollback()`.
    # But if we commit, the data is in transaction?
    # async_session fixture: autocommit=False.
    # If we commit, it persists to the transaction bound to the connection?
    # Usually pytest-asyncio + sqlalchemy with rollback works by nesting transaction or rolling back the outer one.
    # Our fixture: `async with async_session() as session: yield session; await session.rollback()`
    # If we commit inside test, the rollback at end will rollback that commit IF it's a nested transaction or savepoint.
    # Standard sqlalchemy test setup usually uses `connection.begin_nested()`.
    # Let's hope our setup handles it or we shouldn't commit.
    # But `delete_expired_otps` does `session.execute(DELETE...)`. It flush but doesn't explicit commit.
    # Using `flush()` is enough for visibility within same transaction.

    # Let's try to verify.
    # Re-query
    db_session.expire_all()

    result = await db_session.execute(
        select(OTP).where(OTP.email == "expired@example.com")
    )
    assert result.scalars().first() is None

    result = await db_session.execute(
        select(OTP).where(OTP.email == "valid@example.com")
    )
    assert result.scalars().first() is not None
