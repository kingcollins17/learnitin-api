"""Course generation service using AI."""
import re
from fastapi import HTTPException, status
from typing import List, Union
from pydantic import BaseModel
from app.features.courses.schemas import (
    CourseGenerationRequest,
    CourseOutline,
    ModuleOverview,
    LessonOverview,
)
from app.services.langchain_service import LangChainService
from app.features.subscriptions.models import Subscription, SubscriptionResourceType
from app.features.subscriptions.usage_service import SubscriptionUsageService
from typing import List, Union, Optional


class CourseGenerationService:
    """Service for AI-powered course generation."""

    def __init__(self, ai_service: LangChainService):
        self.ai_service = ai_service

    async def generate_courses(
        self,
        request: CourseGenerationRequest,
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
        # Determine number of weeks and credit cost from duration_preference
        
        weeks = 4  # Default to 4 weeks
        duration_pref = request.duration_preference or "4 weeks"
        
        # Try to find a number of weeks in duration preference (e.g. "4 weeks", "5 weeks", "12 weeks")
        match = re.search(r'(\d+)\s*week', duration_pref, re.IGNORECASE)
        if match:
            try:
                weeks = int(match.group(1))
            except ValueError:
                pass
        # Define free lesson rules depending on course size
        free_lessons_rule = (
            "All lessons in the first module (Module 1) must be completely free (set `credit_cost`, `audio_credit_cost`, and `quiz_credit_cost` to 0)."
            if weeks >= 4 else
            "The first 3 lessons of the first module must be completely free (set `credit_cost`, `audio_credit_cost`, and `quiz_credit_cost` to 0)."
        )

        # Build the system prompt
        system_prompt = f"""You are an expert curriculum designer and educational content creator.
Your task is to create comprehensive, well-structured course curricula that help learners achieve their goals.

For each course you design:
- You must structure the course into exactly {weeks} modules (one module for each week of the requested course duration).
- You must assign a `credit_cost`, `audio_credit_cost`, and `quiz_credit_cost` to every lesson in each module according to these pricing rules:
  * Free Lessons: {free_lessons_rule}
  * Paid Lessons (all other lessons): `credit_cost` must be between 20 to 25 credits depending on the complexity of the lesson, `audio_credit_cost` must be between 25 to 30 credits depending on course/lesson complexity, and `quiz_credit_cost` must be between 15 to 20 credits depending on complexity.
- Break down complex topics into logical, progressive modules
- Ensure each module builds upon previous knowledge
- Create specific, actionable learning objectives for each lesson
- Provide realistic time estimates for completion
- Tailor the content to the specified difficulty level
- Make the content engaging and practical

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
Preferred Duration: {request.duration_preference} (exactly {weeks} weeks){learning_goals_text}

Please generate 1-2 course options that cover this topic effectively. Each course should have:
- A clear, descriptive title
- An overview description
- Exactly {weeks} modules (one module representing each week of study)
- Each module should contain 3-5 lessons
- Every lesson must have:
  * Specific learning objectives
  * Duration estimates
  * A `credit_cost` (0 if free, 20-25 if paid)
  * An `audio_credit_cost` (0 if free, 25-30 if paid)
  * A `quiz_credit_cost` (0 if free, 15-20 if paid)

Pricing Guidelines for Lessons:
- {free_lessons_rule}
- For all other lessons, assign a `credit_cost` between 20 and 25 credits based on lesson complexity, an `audio_credit_cost` between 25 and 30 credits, and a `quiz_credit_cost` between 15 and 20 credits.

Make the courses practical, engaging, and suitable for {request.level} learners."""

        # Define the response schema for structured output
        class CoursesResponse(BaseModel):
            """Response containing multiple course outlines."""

            courses: List[CourseOutline]

        # Use LangChain service to generate courses
        response: Union[CoursesResponse, str] = await self.ai_service.invoke(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_schema=CoursesResponse,
        )
        if isinstance(response, str):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate courses: {response}",
            )

        return response.courses
