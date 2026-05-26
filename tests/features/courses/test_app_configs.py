import pytest
from datetime import datetime, timezone
from app.features.app_configs.models import AppConfig
from app.features.app_configs.schemas import AppConfigResponse


def test_app_config_response_validation():
    """Verify that AppConfigResponse correctly maps from an AppConfig database model.
    
    This ensures that the 'metadata' field correctly retrieves metadata_json and
    does not collide with SQLAlchemy's class-level .metadata property.
    """
    model = AppConfig(
        id=123,
        key="test_config_key",
        value="test_value",
        metadata_json={"custom_flag": True, "nested": {"key": "val"}},
        created_at=datetime.now(timezone.utc),
        updated_at=None,
    )
    
    # Validate from ORM model
    response = AppConfigResponse.model_validate(model)
    
    # Assert correct values are parsed
    assert response.id == 123
    assert response.key == "test_config_key"
    assert response.value == "test_value"
    
    # Verify metadata_json is correctly mapped
    assert response.metadata_json == {"custom_flag": True, "nested": {"key": "val"}}
    
    # Verify dump / serialization produces 'metadata' key (alias)
    serialized = response.model_dump(by_alias=True)
    assert "metadata" in serialized
    assert serialized["metadata"] == {"custom_flag": True, "nested": {"key": "val"}}
    assert "metadata_json" not in serialized
