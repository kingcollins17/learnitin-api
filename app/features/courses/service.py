"""Course business logic and service layer."""
from fastapi import HTTPException, status
from typing import List, Optional, Union
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.courses.repository import CourseRepository
from app.features.courses.schemas import (
    CourseGenerationRequest,
    CourseOutline,
    ModuleOverview,
    LessonOverview, CourseResponse
)
from app.services.langchain_service import langchain_service


class CourseService:
    """Service for course business logic."""
    
    def __init__(self, session: AsyncSession):
        self.repository = CourseRepository(session)
    
    async def generate_courses(
        self,
        request: CourseGenerationRequest
    ) -> List[CourseOutline]:
        """
        Generate personalized course curricula using LangChain.
        
        This method uses the LangChain service to create course outlines
        based on the user's topic, level, and learning goals. The generated
        courses are NOT saved to the database.
        
        Args:
            request: Course generation request with topic, level, and preferences
            
        Returns:
            List of generated course outlines with modules and lessons
        """
        # Build the system prompt
        system_prompt = """You are an expert curriculum designer and educational content creator.
Your task is to create comprehensive, well-structured course curricula that help learners achieve their goals.

For each course you design:
- Break down complex topics into logical, progressive modules
- Ensure each module builds upon previous knowledge
- Create specific, actionable learning objectives for each lesson
- Provide realistic time estimates for completion
- Tailor the content to the specified difficulty level
- Make the content engaging and practical

**IMPORTANT - Credit Cost Assignment:**
- Assign a credit_cost to each lesson (integer from 0 to 10)
- The FIRST 2-3 lessons in the ENTIRE COURSE should have credit_cost = 0 (free preview lessons)
- After the free lessons, assign credit costs based on lesson complexity and value:
  * Basic/introductory lessons: 1-3 credits
  * Intermediate lessons with practical exercises: 4-6 credits
  * Advanced lessons with complex topics: 7-8 credits
  * Capstone/project lessons: 9-10 credits
- Consider the difficulty level when assigning costs (beginner courses should have lower costs overall)

Always structure your response as a list of courses, even if generating just one course."""

        # Build the user prompt with request details
        learning_goals_text = ""
        if request.learning_goals:
            goals_list = "\n".join(f"- {goal}" for goal in request.learning_goals)
            learning_goals_text = f"\n\nSpecific learning goals:\n{goals_list}"
        
        user_prompt = f"""Create a comprehensive course curriculum for the following:

Topic: {request.topic}
Difficulty Level: {request.level}
Learning Pace: {request.learning_pace}
Preferred Duration: {request.duration_preference}{learning_goals_text}

Please generate 1-2 course options that cover this topic effectively. Each course should have:
- A clear, descriptive title
- An overview description
- Multiple modules that progressively build knowledge
- Each module should contain 3-5 lessons
- Each lesson should have:
  * Specific learning objectives
  * Duration estimates
  * A credit_cost value (0-10) following the rules:
    - First 2-3 lessons of the course: credit_cost = 0 (free)
    - Remaining lessons: credit_cost based on complexity (1-10)

Make the courses practical, engaging, and suitable for {request.level} learners.
Remember to assign appropriate credit costs to enable a freemium model with free preview lessons."""

        # Define the response schema for structured output
        class CoursesResponse(BaseModel):
            """Response containing multiple course outlines."""
            courses: List[CourseOutline]
        
        # Use LangChain service to generate courses
        response: Union[CoursesResponse, str] = await langchain_service.invoke(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_schema=CoursesResponse
        )
        # if isinstance(response, CourseResponse):

        return response.courses
        # raise HTTPException(detail=f"Failed to generate courses: {response}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

