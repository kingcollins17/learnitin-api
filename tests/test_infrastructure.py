"""
Quick test to verify pytest setup without requiring database.
This tests the test infrastructure itself.
"""
import pytest


def test_pytest_works():
    """Verify pytest is working."""
    assert True


def test_imports():
    """Test that test utilities can be imported."""
    from tests.utils.factories import generate_user_data
    
    user_data = generate_user_data()
    assert "email" in user_data
    assert "username" in user_data
    assert "password" in user_data


@pytest.mark.asyncio
async def test_async_support():
    """Verify async test support works."""
    import asyncio
    await asyncio.sleep(0.001)
    assert True


def test_faker_integration():
    """Test Faker integration."""
    from tests.utils.factories import generate_multiple_users
    
    users = generate_multiple_users(3)
    assert len(users) == 3
    assert all("email" in user for user in users)
