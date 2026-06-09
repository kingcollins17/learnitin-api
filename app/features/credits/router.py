"""Credit API endpoints.

User-facing:
    GET  /credits/balance  — Current credit balance
    GET  /credits/history  — Paginated transaction history

Admin:
    POST /credits/admin/grant    — Grant or revoke credits for a user
    GET  /credits/admin/history  — View any user's credit history
"""

import traceback
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.common.deps import get_current_active_user
from app.common.responses import ApiResponse, success_response
from app.common.events import LogEvent, LogLevel, event_bus
from app.features.users.models import User
from app.common.dependencies import get_credit_service
from .models import CreditTransactionType
from .schemas import (
    CreditBalanceResponse,
    CreditHistoryResponse,
    CreditLedgerEntryResponse,
    AdminCreditGrantRequest,
)
from .service import CreditService

router = APIRouter()


# ==================== User Endpoints ====================


@router.get("/balance", response_model=ApiResponse[CreditBalanceResponse])
async def get_credit_balance(
    current_user: User = Depends(get_current_active_user),
    credit_service: CreditService = Depends(get_credit_service),
):
    """Get the current user's credit balance."""
    try:
        balance = await credit_service.get_balance(current_user.id)  # type: ignore
        return success_response(
            data=CreditBalanceResponse(balance=balance),
            details="Credit balance retrieved successfully.",
        )
    except HTTPException:
        raise
    except Exception as e:
        await event_bus.dispatch(
            LogEvent(
                level=LogLevel.ERROR,
                message=f"Failed to get credit balance for user {current_user.id}",
                data={"error": str(e), "stacktrace": traceback.format_exc()},
            )
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve credit balance. Please try again later.",
        )


@router.get("/history", response_model=ApiResponse[CreditHistoryResponse])
async def get_credit_history(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
    transaction_type: Optional[CreditTransactionType] = Query(default=None),
    current_user: User = Depends(get_current_active_user),
    credit_service: CreditService = Depends(get_credit_service),
):
    """Get the current user's paginated credit transaction history."""
    try:
        skip = (page - 1) * per_page
        entries, total = await credit_service.get_history(
            user_id=current_user.id,  # type: ignore
            skip=skip,
            limit=per_page,
            transaction_type=transaction_type,
        )
        balance = await credit_service.get_balance(current_user.id)  # type: ignore
        return success_response(
            data=CreditHistoryResponse(
                entries=[CreditLedgerEntryResponse.model_validate(e) for e in entries],
                total=total,
                balance=balance,
            ),
            details="Credit history retrieved successfully.",
        )
    except HTTPException:
        raise
    except Exception as e:
        await event_bus.dispatch(
            LogEvent(
                level=LogLevel.ERROR,
                message=f"Failed to get credit history for user {current_user.id}",
                data={"error": str(e), "stacktrace": traceback.format_exc()},
            )
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve credit history. Please try again later.",
        )


# ==================== Admin Endpoints ====================


@router.post("/admin/grant", response_model=ApiResponse[CreditLedgerEntryResponse])
async def admin_grant_credits(
    request: AdminCreditGrantRequest,
    current_user: User = Depends(get_current_active_user),
    credit_service: CreditService = Depends(get_credit_service),
):
    """Admin: Grant or revoke credits for a user.

    Positive amount grants credits, negative amount revokes them.
    Requires superuser privileges.
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required.",
        )

    if request.amount == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Amount must be non-zero.",
        )

    try:
        if request.amount > 0:
            entry = await credit_service.add_credits(
                user_id=request.user_id,
                amount=request.amount,
                transaction_type=CreditTransactionType.ADMIN_GRANT,
                description=request.description,
            )
        else:
            # Revoke = spend credits via admin
            entry = await credit_service.spend_credits(
                user_id=request.user_id,
                amount=abs(request.amount),
                transaction_type=CreditTransactionType.ADMIN_GRANT,
                description=f"[REVOKE] {request.description}",
            )

        await credit_service.commit_all()
        return success_response(
            data=CreditLedgerEntryResponse.model_validate(entry),
            details=f"Credits {'granted' if request.amount > 0 else 'revoked'} successfully.",
            status_code=201,
        )
    except HTTPException:
        raise
    except Exception as e:
        await event_bus.dispatch(
            LogEvent(
                level=LogLevel.ERROR,
                message=f"Failed to grant credits to user {request.user_id}",
                data={
                    "admin_id": current_user.id,
                    "target_user_id": request.user_id,
                    "amount": request.amount,
                    "error": str(e),
                    "stacktrace": traceback.format_exc(),
                },
            )
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process credit operation. Please try again later.",
        )


@router.get(
    "/admin/history", response_model=ApiResponse[CreditHistoryResponse]
)
async def admin_get_user_credit_history(
    user_id: int = Query(..., description="Target user ID"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
    transaction_type: Optional[CreditTransactionType] = Query(default=None),
    current_user: User = Depends(get_current_active_user),
    credit_service: CreditService = Depends(get_credit_service),
):
    """Admin: View any user's credit history and balance."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required.",
        )

    try:
        skip = (page - 1) * per_page
        entries, total = await credit_service.get_history(
            user_id=user_id,
            skip=skip,
            limit=per_page,
            transaction_type=transaction_type,
        )
        balance = await credit_service.get_balance(user_id)
        return success_response(
            data=CreditHistoryResponse(
                entries=[CreditLedgerEntryResponse.model_validate(e) for e in entries],
                total=total,
                balance=balance,
            ),
            details="User credit history retrieved successfully.",
        )
    except HTTPException:
        raise
    except Exception as e:
        await event_bus.dispatch(
            LogEvent(
                level=LogLevel.ERROR,
                message=f"Failed to get credit history for user {user_id}",
                data={
                    "admin_id": current_user.id,
                    "target_user_id": user_id,
                    "error": str(e),
                    "stacktrace": traceback.format_exc(),
                },
            )
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve credit history. Please try again later.",
        )
