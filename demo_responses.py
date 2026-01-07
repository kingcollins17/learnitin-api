"""
Demo script to test the generic API response structure.
"""
from app.common.responses import ApiResponse, success_response, error_response
from app.features.users.schemas import UserResponse
from datetime import datetime, timezone


def demo():
    """Demonstrate the generic response structure."""
    print("=" * 60)
    print("Generic API Response Structure Demo")
    print("=" * 60)
    
    # Test 1: Success response with user data
    print("\n1. Success Response with User Data:")
    print("-" * 40)
    
    user_data = UserResponse(
        id=1,
        email="user@example.com",
        username="john_doe",
        full_name="John Doe",
        is_active=True,
        is_superuser=False,
        created_at=datetime.now(timezone.utc),
        updated_at=None
    )
    
    response = success_response(
        data=user_data,
        details="User retrieved successfully"
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Details: {response.details}")
    print(f"Data Type: {type(response.data)}")
    print(f"User Email: {response.data.email}")
    
    # Test 2: Success response with list
    print("\n2. Success Response with List:")
    print("-" * 40)
    
    users_list = [user_data]
    response2 = success_response(
        data=users_list,
        details=f"Retrieved {len(users_list)} users"
    )
    
    print(f"Status Code: {response2.status_code}")
    print(f"Details: {response2.details}")
    print(f"Data Type: {type(response2.data)}")
    print(f"Number of Users: {len(response2.data)}")
    
    # Test 3: Error response
    print("\n3. Error Response:")
    print("-" * 40)
    
    error = error_response(
        details="User not found",
        status_code=404
    )
    
    print(f"Status Code: {error.status_code}")
    print(f"Details: {error.details}")
    print(f"Data: {error.data}")
    
    # Test 4: Created response
    print("\n4. Created Response (201):")
    print("-" * 40)
    
    created = success_response(
        data=user_data,
        details="User created successfully",
        status_code=201
    )
    
    print(f"Status Code: {created.status_code}")
    print(f"Details: {created.details}")
    
    print("\n" + "=" * 60)
    print("✓ All response types working correctly!")
    print("=" * 60)


if __name__ == "__main__":
    demo()
