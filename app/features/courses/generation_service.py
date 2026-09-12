"""Course generation service using AI."""
import re
from fastapi import HTTPException, status
from typing import List, Union
from pydantic import BaseModel
from app.features.courses.models import CourseLevel
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
        # Recommended free course topics
        RECOMMENDED_FREE_COURSES = [
            "Virtual Assistance",
            "Social Media Management",
            "Digital Marketing",
            "Freelancing",
            "Canva and Graphic Design",
            "Excel",
            "Data Analysis",
            "AI for Beginners",
        ]

        topic_lower = request.topic.lower()
        is_recommended_free = any(
            kw.lower() in topic_lower or topic_lower in kw.lower()
            for kw in RECOMMENDED_FREE_COURSES
        ) or ("canva" in topic_lower) or ("graphic design" in topic_lower) or ("ai" in topic_lower and "beginner" in topic_lower)

        # Define free lesson rules depending on topic and course size
        if is_recommended_free:
            free_lessons_rule = (
                "This topic is in our recommended free courses list (Virtual Assistance, Social Media Management, Digital Marketing, Freelancing, Canva and Graphic Design, Excel, Data Analysis, AI for Beginners). "
                "Make this course free for the most part: set `credit_cost`, `audio_credit_cost`, and `quiz_credit_cost` to 0 for all or almost all lessons across all modules."
            )
        elif weeks >= 4:
            free_lessons_rule = (
                "All lessons in the first module (Module 1) must be completely free (set `credit_cost`, `audio_credit_cost`, and `quiz_credit_cost` to 0)."
            )
        else:
            free_lessons_rule = (
                "The first 3 lessons of the first module must be completely free (set `credit_cost`, `audio_credit_cost`, and `quiz_credit_cost` to 0)."
            )

        # Determine level-based credit costs (Beginner < Intermediate < Expert)
        level_val = (
            request.level.value
            if isinstance(request.level, CourseLevel)
            else str(request.level)
        ).lower()

        if level_val == "beginner":
            credit_range = "30-50"
            audio_range = "40-60"
            quiz_range = "20-35"
        elif level_val == "expert":
            credit_range = "80-120"
            audio_range = "100-150"
            quiz_range = "50-75"
        else:  # intermediate or default
            credit_range = "50-75"
            audio_range = "70-100"
            quiz_range = "35-50"

        level_pricing_rule = (
            f"For {request.level} level paid lessons: `credit_cost` must be {credit_range} credits based on lesson complexity, "
            f"`audio_credit_cost` must be {audio_range} credits, and `quiz_credit_cost` must be {quiz_range} credits."
        )

        # Build the system prompt
        system_prompt = f"""You are an expert curriculum designer and educational content creator.
Your task is to create comprehensive, well-structured course curricula that help learners achieve their goals.

For each course you design:
- You must structure the course into exactly {weeks} modules (one module for each week of the requested course duration).
- You must assign a `credit_cost`, `audio_credit_cost`, and `quiz_credit_cost` to every lesson in each module according to these pricing rules:
  * Free Lessons Guidelines: {free_lessons_rule}
  * Recommended Free Courses: Recommended free courses to start with include: Virtual Assistance, Social Media Management, Digital Marketing, Freelancing, Canva and Graphic Design, Excel, Data Analysis, AI for Beginners. If the requested course topic belongs to these recommended free topics, make the course free for the most part by setting `credit_cost`, `audio_credit_cost`, and `quiz_credit_cost` to 0 for almost all or all lessons.
  * Level-Based Paid Lessons Pricing Tier Guidelines:
    - Beginner courses: lower cost (`credit_cost`: 30-50, `audio_credit_cost`: 40-60, `quiz_credit_cost`: 20-35 credits)
    - Intermediate courses: moderate cost (`credit_cost`: 50-75, `audio_credit_cost`: 70-100, `quiz_credit_cost`: 35-50 credits)
    - Expert courses: higher cost (`credit_cost`: 80-120, `audio_credit_cost`: 100-150, `quiz_credit_cost`: 50-75 credits)
  * Target Level Pricing ({request.level}): {level_pricing_rule}
- Break down complex topics into logical, progressive modules
- Ensure each module builds upon previous knowledge
- Create specific, actionable learning objectives for each lesson
- Provide realistic time estimates for completion
- Tailor the content to the specified difficulty level ({request.level})
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
  * A `credit_cost` (0 if free, otherwise {credit_range} for paid lessons based on {request.level} difficulty)
  * An `audio_credit_cost` (0 if free, otherwise {audio_range} for paid lessons based on {request.level} difficulty)
  * A `quiz_credit_cost` (0 if free, otherwise {quiz_range} for paid lessons based on {request.level} difficulty)

Pricing Guidelines for Lessons:
- {free_lessons_rule}
- {level_pricing_rule}

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
