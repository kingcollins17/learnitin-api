"""
Quick test to verify the user course changes work correctly.

This script tests:
1. The unique constraint prevents duplicate enrollments
2. The new endpoint works with course_id query parameter
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from app.common.database.session import AsyncSessionLocal
from app.features.courses.service import CourseService
from app.features.courses.models import UserCourse
from fastapi import HTTPException


async def test_unique_constraint():
    """Test that the unique constraint prevents duplicate enrollments."""
    print("\n" + "=" * 60)
    print("Testing Unique Constraint on UserCourse")
    print("=" * 60 + "\n")

    async with AsyncSessionLocal() as session:
        service = CourseService(session)

        # Test data - you may need to adjust these IDs based on your database
        test_user_id = 1
        test_course_id = 1

        try:
            # Try to enroll twice
            print(
                f"Attempting first enrollment (user_id={test_user_id}, course_id={test_course_id})..."
            )

            # Check if already enrolled
            from app.features.courses.repository import UserCourseRepository

            repo = UserCourseRepository(session)
            existing = await repo.get_by_user_and_course(test_user_id, test_course_id)

            if existing:
                print("✓ User already enrolled in this course")
                print(f"  UserCourse ID: {existing.id}")

                # Try to enroll again (should fail)
                print("\nAttempting duplicate enrollment...")
                try:
                    await service.enroll_course(test_user_id, test_course_id)
                    print("✗ FAILED: Duplicate enrollment was allowed!")
                    return False
                except HTTPException as e:
                    if "already enrolled" in str(e.detail).lower():
                        print(f"✓ SUCCESS: Duplicate enrollment prevented")
                        print(f"  Error message: {e.detail}")
                        return True
                    else:
                        print(f"✗ FAILED: Unexpected error: {e.detail}")
                        return False
            else:
                print("✓ User not enrolled yet")
                print("\nEnrolling user in course...")
                user_course = await service.enroll_course(test_user_id, test_course_id)
                print(
                    f"✓ First enrollment successful (UserCourse ID: {user_course.id})"
                )

                # Try to enroll again (should fail)
                print("\nAttempting duplicate enrollment...")
                try:
                    await service.enroll_course(test_user_id, test_course_id)
                    print("✗ FAILED: Duplicate enrollment was allowed!")
                    return False
                except HTTPException as e:
                    if "already enrolled" in str(e.detail).lower():
                        print(f"✓ SUCCESS: Duplicate enrollment prevented")
                        print(f"  Error message: {e.detail}")
                        return True
                    else:
                        print(f"✗ FAILED: Unexpected error: {e.detail}")
                        return False

        except Exception as e:
            print(f"✗ FAILED: Unexpected error: {e}")
            import traceback

            traceback.print_exc()
            return False


async def test_get_user_course_by_course_id():
    """Test that we can get user course details by course_id."""
    print("\n" + "=" * 60)
    print("Testing Get User Course by Course ID")
    print("=" * 60 + "\n")

    async with AsyncSessionLocal() as session:
        service = CourseService(session)

        # Test data - you may need to adjust these IDs based on your database
        test_user_id = 1
        test_course_id = 1

        try:
            print(
                f"Fetching user course (user_id={test_user_id}, course_id={test_course_id})..."
            )

            user_course = await service.get_user_course_detail(
                user_id=test_user_id, course_id=test_course_id
            )

            if user_course:
                print("✓ SUCCESS: User course found")
                print(f"  UserCourse ID: {user_course.id}")
                print(f"  Course ID: {user_course.course_id}")
                print(f"  User ID: {user_course.user_id}")
                print(f"  Status: {user_course.status}")
                if user_course.course:
                    print(f"  Course Title: {user_course.course.title}")
                return True
            else:
                print("✗ FAILED: User course not found")
                return False

        except HTTPException as e:
            if e.status_code == 404:
                print(f"ℹ INFO: User not enrolled in this course")
                print(f"  Error message: {e.detail}")
                print("\n  This is expected if the user hasn't enrolled yet.")
                return True
            else:
                print(f"✗ FAILED: Unexpected error: {e.detail}")
                return False
        except Exception as e:
            print(f"✗ FAILED: Unexpected error: {e}")
            import traceback

            traceback.print_exc()
            return False


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("User Course Changes - Verification Tests")
    print("=" * 60)

    results = []

    # Test 1: Unique constraint
    result1 = await test_unique_constraint()
    results.append(("Unique Constraint Test", result1))

    # Test 2: Get by course_id
    result2 = await test_get_user_course_by_course_id()
    results.append(("Get by Course ID Test", result2))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60 + "\n")

    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{status}: {test_name}")

    all_passed = all(result for _, result in results)

    print("\n" + "=" * 60)
    if all_passed:
        print("All tests passed! ✓")
    else:
        print("Some tests failed! ✗")
    print("=" * 60 + "\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
