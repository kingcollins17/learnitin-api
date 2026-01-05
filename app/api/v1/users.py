from fastapi import APIRouter, Depends
from app.core.deps import get_current_active_user
from app.models.user import User as UserModel
from app.schemas.user import User

router = APIRouter()

@router.get("/me", response_model=User)
async def read_users_me(current_user: UserModel = Depends(get_current_active_user)):
    """Get current user information."""
    return current_user

@router.get("/{user_id}", response_model=User)
async def read_user(
    user_id: int,
    current_user: UserModel = Depends(get_current_active_user)
):
    """Get user by ID (requires authentication)."""
    # Add authorization logic here if needed
    return current_user
