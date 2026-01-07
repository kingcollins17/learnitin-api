"""Tests for course service."""
import pytest
from unittest.mock import AsyncMock, patch
from app.features.courses.service import CourseService
from app.features.courses.schemas import (
    CourseGenerationRequest,
    CourseOutline,
    ModuleOverview,
    LessonOverview
)


class TestCourseService:
    """Test suite for course service."""
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        return AsyncMock()
    
    @pytest.fixture
    def service(self, mock_session):
        """Create a course service instance."""
        return CourseService(mock_session)
    
    @pytest.mark.asyncio
    async def test_generate_courses_basic(self, service):
        """Test basic course generation."""
        request = CourseGenerationRequest(
            topic="Python Programming",
            level="beginner",
            duration_preference="4 weeks"
        )
        
        # Mock the LangChain service response
        mock_courses = [
            CourseOutline(
                title="Introduction to Python",
                description="Learn Python basics",
                duration="4 weeks",
                outline=[
                    ModuleOverview(
                        title="Getting Started",
                        description="Python fundamentals",
                        duration="1 week",
                        lessons=[
                            LessonOverview(
                                title="Variables and Data Types",
                                objectives=["Understand variables", "Learn data types"],
                                duration="2 hours"
                            )
                        ]
                    )
                ]
            )
        ]
        
        with patch('app.features.courses.service.langchain_service.invoke') as mock_invoke:
            # Create a mock response object
            class MockResponse:
                courses = mock_courses
            
            mock_invoke.return_value = MockResponse()
            
            # Generate courses
            courses = await service.generate_courses(request)
            
            # Assertions
            assert len(courses) > 0
            assert isinstance(courses[0], CourseOutline)
            assert courses[0].title == "Introduction to Python"
            assert len(courses[0].outline) > 0
            assert len(courses[0].outline[0].lessons) > 0
    
    @pytest.mark.asyncio
    async def test_generate_courses_with_goals(self, service):
        """Test course generation with specific learning goals."""
        request = CourseGenerationRequest(
            topic="Data Science",
            level="intermediate",
            duration_preference="8 weeks",
            learning_goals=["Learn pandas", "Master visualization", "Understand statistics"]
        )
        
        mock_courses = [
            CourseOutline(
                title="Data Science Fundamentals",
                description="Comprehensive data science course",
                duration="8 weeks",
                outline=[
                    ModuleOverview(
                        title="Data Analysis with Pandas",
                        description="Master pandas library",
                        duration="2 weeks",
                        lessons=[
                            LessonOverview(
                                title="Introduction to Pandas",
                                objectives=["Learn DataFrame basics"],
                                duration="3 hours"
                            )
                        ]
                    )
                ]
            )
        ]
        
        with patch('app.features.courses.service.langchain_service.invoke') as mock_invoke:
            class MockResponse:
                courses = mock_courses
            
            mock_invoke.return_value = MockResponse()
            
            courses = await service.generate_courses(request)
            
            assert len(courses) > 0
            assert isinstance(courses[0], CourseOutline)
            
            # Verify that invoke was called with the correct arguments
            mock_invoke.assert_called_once()
            call_kwargs = mock_invoke.call_args.kwargs
            assert "system_prompt" in call_kwargs
            assert "user_prompt" in call_kwargs
            assert "response_schema" in call_kwargs
            
            # Check that learning goals are in the user prompt
            user_prompt = call_kwargs["user_prompt"]
            assert "pandas" in user_prompt.lower()
            assert "visualization" in user_prompt.lower()
