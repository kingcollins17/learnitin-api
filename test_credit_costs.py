"""
Test script to verify credit cost assignment in course generation.
"""
import asyncio
from app.features.courses.schemas import CourseGenerationRequest
from app.features.courses.service import CourseService
from unittest.mock import AsyncMock


async def test_credit_costs():
    """Test that credit costs are properly assigned to lessons."""
    print("=" * 60)
    print("Credit Cost Assignment Test")
    print("=" * 60)
    
    mock_session = AsyncMock()
    service = CourseService(mock_session)
    
    request = CourseGenerationRequest(
        topic="Python Web Development",
        level="intermediate",
        learning_pace="balanced",
        duration_preference="6 weeks"
    )
    
    print(f"\nGenerating course for: {request.topic}")
    print(f"Level: {request.level}")
    print(f"Duration: {request.duration_preference}")
    print("-" * 60)
    
    try:
        courses = await service.generate_courses(request)
        
        for i, course in enumerate(courses, 1):
            print(f"\n📚 Course {i}: {course.title}")
            print(f"Duration: {course.duration}")
            print(f"Modules: {len(course.outline)}")
            
            lesson_count = 0
            free_lessons = 0
            paid_lessons = 0
            
            for j, module in enumerate(course.outline, 1):
                print(f"\n  📖 Module {j}: {module.title}")
                
                for k, lesson in enumerate(module.lessons, 1):
                    lesson_count += 1
                    cost = getattr(lesson, 'credit_cost', 0)
                    
                    if cost == 0:
                        free_lessons += 1
                        status = "🆓 FREE"
                    else:
                        paid_lessons += 1
                        status = f"💰 {cost} credits"
                    
                    print(f"    Lesson {k}: {lesson.title} - {status}")
            
            print(f"\n  Summary:")
            print(f"  Total Lessons: {lesson_count}")
            print(f"  Free Lessons: {free_lessons}")
            print(f"  Paid Lessons: {paid_lessons}")
            
            # Verify first 2-3 lessons are free
            first_lessons_free = True
            lesson_idx = 0
            for module in course.outline:
                for lesson in module.lessons:
                    lesson_idx += 1
                    if lesson_idx <= 3:
                        cost = getattr(lesson, 'credit_cost', 0)
                        if cost != 0:
                            first_lessons_free = False
                            print(f"  ⚠️  Warning: Lesson {lesson_idx} should be free but costs {cost} credits")
            
            if first_lessons_free:
                print(f"  ✅ First 2-3 lessons are free as expected")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n" + "=" * 60)
    print("✅ Credit cost test completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_credit_costs())
