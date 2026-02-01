"""Authentication API endpoints."""

from fastapi import APIRouter, Depends, status, HTTPException
import traceback
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.database.session import get_async_session
from app.common.responses import ApiResponse, success_response
from app.features.auth.otp_service import OTPService
from app.features.users.schemas import UserCreate, UserResponse
from app.services.email_service import email_service
from app.features.auth.schemas import (
    Token,
    GoogleLoginRequest,
    TestEmailRequest,
    MagicLinkLoginRequest,
    ResetPasswordRequest,
)
from app.features.auth.service import AuthService
from app.features.auth.otp_repository import OTPRepository
from app.features.auth.otp_schemas import (
    OTPRequest,
    OTPResponse,
    OTPVerify,
    MagicLinkRequest,
)

router = APIRouter()


def get_otp_service(session: AsyncSession = Depends(get_async_session)) -> OTPService:
    return OTPService(session)


@router.post(
    "/register",
    response_model=ApiResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
)
async def register(
    user_data: UserCreate, session: AsyncSession = Depends(get_async_session)
):
    """
    Register a new user.

    Creates a new user account with `is_active=False`. Users must verify their account
    (typically via OTP sent to their email) before they can access protected resources.

    **Request Body:**
    - `email`: User's email address (must be unique)
    - `username`: User's username (must be unique)
    - `password`: User's password (will be hashed using Argon2)
    - `full_name`: Optional full name

    **Response:**
    Returns the created user with `is_active=False`. The user should:
    1. Login via `/api/v1/auth/login` (allowed even with is_active=False)
    2. Request an OTP via `/api/v1/auth/otp/request`
    3. Verify their account via `/api/v1/users/verify` with the OTP code (requires authentication)

    **Error Responses:**
    - `400 Bad Request`: Email or username already exists
    - `500 Internal Server Error`: Server error
    """
    try:
        service = AuthService(session)
        user = await service.register_user(user_data)

        # Automatically request verification magic link
        otp_service = OTPService(session)
        await otp_service.request_magic_link(
            email=user.email, request_type="verification"
        )

        return success_response(
            data=user,
            details="User registered successfully. Please check your email for a verification link to activate your account.",
            status_code=201,
        )
    except HTTPException:
        traceback.print_exc()
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register user: {str(e)}",
        )


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Login and get access token.

    **Important:** Users can sign in even if their account is not verified (is_active=False).
    The response includes an `is_active` field that clients should check to determine if
    the user needs to verify their account before accessing protected resources.

    **Request Body (OAuth2 form):**
    - `username`: User's email address
    - `password`: User's password

    **Response:**
    - `access_token`: JWT token for authentication
    - `token_type`: Always "bearer"
    - `user_id`: User's unique ID
    - `email`: User's email address
    - `username`: User's username
    - `is_active`: Whether the user's account is verified/active

    **Client Flow:**
    1. Call this endpoint with credentials
    2. Check the `is_active` field in the response
    3. If `is_active` is `false`, prompt the user to verify their account (e.g., via OTP)
    4. If `is_active` is `true`, proceed with normal authenticated flow

    **Note:** Some endpoints may still require an active account (using `get_current_active_user` dependency).
    Inactive users will receive a 400 error when trying to access those endpoints.

    **Error Responses:**
    - `401 Unauthorized`: Invalid credentials
    - `500 Internal Server Error`: Server error
    """
    try:
        service = AuthService(session)
        token_data = await service.authenticate_and_get_token(
            form_data.username, form_data.password
        )
        return token_data
    except HTTPException:
        traceback.print_exc()
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}",
        )


@router.post("/google", response_model=Token)
async def google_login(
    data: GoogleLoginRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Login with Google.

    Verifies the Google ID provided by the client, checks if the user exists,
    creates the user if not (generating a random password), and returns a JWT token.
    The user is automatically activated since Google verification is trusted.

    **Request Body:**
    - `token`: Google ID token

    **Response:**
    - `access_token`: JWT token for authentication
    - `token_type`: Always "bearer"
    - `user_id`: User's unique ID
    - `email`: User's email address
    - `username`: User's username
    - `is_active`: Always true for Google login
    """
    try:
        service = AuthService(session)
        token_data = await service.authenticate_google_user(data.token)
        return token_data
    except HTTPException:
        traceback.print_exc()
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Google login failed: {str(e)}",
        )


@router.post("/otp/request", response_model=ApiResponse[OTPResponse])
async def request_otp(
    data: OTPRequest,
    service: OTPService = Depends(get_otp_service),
):
    """
    Request a new OTP.

    Generates and sends a 6-digit verification code to the provided email.
    OTP is valid for 10 minutes.
    """
    try:
        await service.request_otp(email=data.email)
        return success_response(
            data=OTPResponse(message="OTP sent successfully", success=True),
            details="OTP sent successfully",
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send OTP",
        )


@router.post("/magic-link/request", response_model=ApiResponse[OTPResponse])
async def request_magic_link(
    data: MagicLinkRequest,
    service: OTPService = Depends(get_otp_service),
):
    """
    Request a passwordless sign-in magic link.

    Generates a magic link and sends it to the provided email.
    The link leads to the zidepeople.com app which then calls the verify endpoint.
    """
    try:
        await service.request_magic_link(email=data.email, request_type=data.type)
        return success_response(
            data=OTPResponse(message="Magic link sent successfully", success=True),
            details="Magic link sent successfully",
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send magic link: {str(e)}",
        )


@router.post("/password-reset/request", response_model=ApiResponse[OTPResponse])
async def request_password_reset(
    data: OTPRequest,
    service: OTPService = Depends(get_otp_service),
):
    """
    Request a password reset OTP.
    """
    try:
        # Use specialized password reset OTP request
        await service.request_password_reset_otp(email=data.email)
        return success_response(
            data=OTPResponse(message="Password reset OTP sent", success=True),
            details="OTP sent successfully",
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send reset OTP: {str(e)}",
        )


@router.post("/password-reset/reset", response_model=ApiResponse[bool])
async def reset_password(
    data: ResetPasswordRequest,
    session: AsyncSession = Depends(get_async_session),
    otp_service: OTPService = Depends(get_otp_service),
):
    """
    Reset password using email, OTP and new password.
    """
    try:
        # 1. Verify OTP
        is_valid = await otp_service.verify_otp(code=data.otp, email=data.email)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OTP",
            )

        # 2. Reset Password
        auth_service = AuthService(session)
        await auth_service.reset_password(data.email, data.new_password)

        await session.commit()

        return success_response(
            data=True,
            details="Password has been reset successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Password reset failed: {str(e)}",
        )


@router.post("/passwordless/verify", response_model=Token)
async def verify_magic_link(
    data: MagicLinkLoginRequest,
    session: AsyncSession = Depends(get_async_session),
    otp_service: OTPService = Depends(get_otp_service),
):
    """
    Verify magic link OTP and login.

    Takes the email and OTP from the magic link, verifies them,
    and returns a standard access token for the user.
    """
    try:
        # 1. Verify OTP
        is_valid = await otp_service.verify_otp(code=data.otp, email=data.email)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired link",
            )

        # 2. Authenticate and get token
        auth_service = AuthService(session)
        user = await auth_service.authenticate_magic_link(data.email)

        # 3. Activation check (if we want to auto-activate magic link users)
        if not user.is_active:
            user.is_active = True
            await auth_service.user_service.repository.update(user)
            await session.commit()

        return auth_service.generate_token_response(user)

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        print(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"link verification failed: we could not verify your link at this time",
        )


@router.post("/otp/verify", response_model=ApiResponse[OTPResponse])
async def verify_otp(
    data: OTPVerify,
    service: OTPService = Depends(get_otp_service),
):
    """
    Verify an OTP code.

    Checks if the provided code is valid and hasn't expired.
    """
    try:
        is_valid = await service.verify_otp(code=data.code, email=data.email)

        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired Link/OTP",
            )

        return success_response(
            data=OTPResponse(message="OTP verified successfully", success=True),
            details="Link/OTP verified successfully",
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Verification failed: {str(e)}",
        )


@router.post("/otp/check", response_model=ApiResponse[bool])
async def check_otp(
    data: OTPVerify,
    service: OTPService = Depends(get_otp_service),
):
    """
    Check if an OTP code is valid without marking it as used.
    """
    try:
        is_valid = await service.check_otp_validity(code=data.code, email=data.email)

        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired Link/OTP",
            )

        return success_response(
            data=True,
            details="Link/OTP is valid",
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OTP check failed: {str(e)}",
        )
