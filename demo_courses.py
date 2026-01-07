"""
Demo script to test course generation feature.
Run this to verify the course generation works end-to-end.
"""
import asyncio
from app.features.courses.schemas import CourseGenerationRequest
from app.features.courses.service import CourseService
from unittest.mock import AsyncMock


async def demo():
    """Run a demo of course generation."""
    print("=" * 60)
    print("Course Generation Demo")
    print("=" * 60)
    
    # Create a mock session (since we're not saving to DB)
    mock_session = AsyncMock()
    service = CourseService(mock_session)
    
    # Test 1: Basic course generation
    print("\n1. Generating Python Course for Beginners:")
    print("-" * 40)
    request = CourseGenerationRequest(
        topic="Python Programming",
        level="beginner",
        duration_preference="4 weeks"
    )
    
    try:
        courses = await service.generate_courses(request)
        
        print(f"\n✓ Generated {len(courses)} course(s)\n")
        
        for i, course in enumerate(courses, 1):
            print(f"Course {i}: {course.title}")
            print(f"Description: {course.description}")
            print(f"Duration: {course.duration}")
            print(f"Modules: {len(course.outline)}")
            
            for j, module in enumerate(course.outline, 1):
                print(f"\n  Module {j}: {module.title}")
                print(f"  Duration: {module.duration}")
                print(f"  Lessons: {len(module.lessons)}")
                
                for k, lesson in enumerate(module.lessons, 1):
                    print(f"    Lesson {k}: {lesson.title}")
                    print(f"    Duration: {lesson.duration}")
                    print(f"    Objectives: {len(lesson.objectives)}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Test 2: Course with specific learning goals
    print("\n\n2. Generating Data Science Course with Goals:")
    print("-" * 40)
    request2 = CourseGenerationRequest(
        topic="Data Science with Python",
        level="intermediate",
        duration_preference="6 weeks",
        learning_goals=[
            "Master pandas for data manipulation",
            "Create visualizations with matplotlib",
            "Understand statistical analysis"
        ]
    )
    
    try:
        courses2 = await service.generate_courses(request2)
        
        print(f"\n✓ Generated {len(courses2)} course(s)\n")
        
        for course in courses2:
            print(f"Course: {course.title}")
            print(f"Modules: {len(course.outline)}")
            total_lessons = sum(len(m.lessons) for m in course.outline)
            print(f"Total Lessons: {total_lessons}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n" + "=" * 60)
    print("✓ Demo completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(demo())
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
