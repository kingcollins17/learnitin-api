"""Course API endpoints."""
from fastapi import APIRouter, Depends, status, HTTPException
import traceback
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.database.session import get_async_session
from app.common.deps import get_current_active_user
from app.common.responses import ApiResponse, success_response
from app.features.users.models import User
from app.features.courses.schemas import (
    CourseGenerationRequest,
    CourseGenerationResponse,
    CourseOutline
)
from app.features.courses.service import CourseService

router = APIRouter()


@router.post("/generate", response_model=ApiResponse[CourseGenerationResponse])
async def generate_courses(
    request: CourseGenerationRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user)
):
    """
    Generate personalized course curricula using AI.
    
    This endpoint uses LangChain to generate comprehensive course outlines
    based on the user's specified topic, level, and learning goals.
    
    The generated courses are NOT saved to the database - they are created
    on-demand for the user to review.
    
    **Authentication required.**
    """
    try:
        service = CourseService(session)
        courses = await service.generate_courses(request)
        
        return success_response(
            data=CourseGenerationResponse(courses=courses),
            details=f"Successfully generated {len(courses)} course(s)"
        )
    except HTTPException:
        traceback.print_exc()
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate courses: {str(e)}"
        )


