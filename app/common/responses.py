"""Generic API response models and helpers."""
from typing import TypeVar, Generic, Optional, Any
from pydantic import BaseModel, Field


T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """
    Generic API response wrapper for all endpoints.
    
    All API responses should use this structure for consistency.
    
    Example:
        ```python
        @router.get("/users/me", response_model=ApiResponse[UserResponse])
        async def get_current_user(...):
            return success_response(
                data=user,
                details="User retrieved successfully"
            )
        ```
    """
    status_code: int = Field(description="HTTP status code")
    details: str = Field(description="Human-readable message describing the response")
    data: Optional[T] = Field(default=None, description="Response data")
    
    class Config:
        from_attributes = True


def success_response(
    data: Any,
    details: str = "Operation successful",
    status_code: int = 200
) -> ApiResponse:
    """
    Create a success response.
    
    Args:
        data: The response data
        details: Success message
        status_code: HTTP status code (default: 200)
        
    Returns:
        ApiResponse with the provided data
        
    Example:
        ```python
        return success_response(
            data=user,
            details="User created successfully",
            status_code=201
        )
        ```
    """
    return ApiResponse(
        status_code=status_code,
        details=details,
        data=data
    )


def error_response(
    details: str,
    status_code: int = 400,
    data: Any = None
) -> ApiResponse:
    """
    Create an error response.
    
    Args:
        details: Error message
        status_code: HTTP status code (default: 400)
        data: Optional error data
        
    Returns:
        ApiResponse with error information
        
    Example:
        ```python
        return error_response(
            details="User not found",
            status_code=404
        )
        ```
    """
    return ApiResponse(
        status_code=status_code,
        details=details,
        data=data
    )
