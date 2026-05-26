import pytest
from httpx import AsyncClient
from app.common.config import settings


@pytest.mark.asyncio
async def test_get_course_credit_cost(client: AsyncClient):
    """Verify that GET /api/v1/courses/credit-cost returns the correct cost from settings."""
    response = await client.get("/api/v1/courses/credit-cost")
    assert response.status_code == 200
    
    body = response.json()
    assert body["success"] is True
    assert "credit_cost" in body["data"]
    assert body["data"]["credit_cost"] == settings.COURSE_GENERATION_COST
    assert body["details"] == "Course credit cost retrieved successfully"
