"""Test utilities and helpers."""
from faker import Faker

fake = Faker()


def generate_user_data(
    email: str | None = None,
    username: str | None = None,
    password: str = "TestPassword123!",
    full_name: str | None = None
) -> dict:
    """Generate random user data for testing."""
    return {
        "email": email or fake.email(),
        "username": username or fake.user_name(),
        "password": password,
        "full_name": full_name or fake.name()
    }


def generate_multiple_users(count: int = 5) -> list[dict]:
    """Generate multiple user data dictionaries."""
    return [generate_user_data() for _ in range(count)]
