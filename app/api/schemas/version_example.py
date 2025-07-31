"""
Example of how to add a new API version (v3) using the scalable schema system.

This demonstrates how easy it is to add new versions without modifying existing code.
"""

from typing import Dict, Any
from pydantic import Field
from .base import BaseSchema, TimestampMixin, IDMixin
from . import add_new_api_version


# Example V3 schemas with new features
class V3BaseSchema(BaseSchema):
    """Base schema for V3 with new features."""
    
    class Config:
        extra = "allow"  # V3 is very flexible
        validate_assignment = True


class UserV3Schema(V3BaseSchema, IDMixin, TimestampMixin):
    """V3 User schema with AI-powered features."""
    
    email: str = Field(description="User email")
    first_name: str = Field(description="First name")
    last_name: str = Field(description="Last name")
    
    # V3 new features
    ai_preferences: Dict[str, Any] = Field(default_factory=dict, description="AI preferences")
    biometric_data: Dict[str, Any] = Field(default_factory=dict, description="Biometric data")
    social_connections: list = Field(default_factory=list, description="Social connections")
    
    # Advanced V3 features
    ml_insights: Dict[str, Any] = Field(default_factory=dict, description="ML-generated insights")
    predictive_health: Dict[str, Any] = Field(default_factory=dict, description="Predictive health data")


class PetV3Schema(V3BaseSchema, IDMixin, TimestampMixin):
    """V3 Pet schema with IoT and AI features."""
    
    name: str = Field(description="Pet name")
    species: str = Field(description="Pet species")
    breed: str = Field(description="Pet breed")
    
    # V3 IoT features
    iot_devices: list = Field(default_factory=list, description="Connected IoT devices")
    real_time_health: Dict[str, Any] = Field(default_factory=dict, description="Real-time health data")
    activity_tracking: Dict[str, Any] = Field(default_factory=dict, description="Activity tracking data")
    
    # V3 AI features
    behavior_analysis: Dict[str, Any] = Field(default_factory=dict, description="AI behavior analysis")
    health_predictions: Dict[str, Any] = Field(default_factory=dict, description="Health predictions")


# Migration functions
def migrate_v2_to_v3(v2_data: Dict[str, Any]) -> Dict[str, Any]:
    """Migrate V2 data to V3 format."""
    v3_data = v2_data.copy()
    
    # Add V3-specific defaults
    v3_data.setdefault("ai_preferences", {})
    v3_data.setdefault("biometric_data", {})
    v3_data.setdefault("social_connections", [])
    v3_data.setdefault("ml_insights", {})
    v3_data.setdefault("predictive_health", {})
    
    # For pets
    if "species" in v3_data:  # This is likely a pet
        v3_data.setdefault("iot_devices", [])
        v3_data.setdefault("real_time_health", {})
        v3_data.setdefault("activity_tracking", {})
        v3_data.setdefault("behavior_analysis", {})
        v3_data.setdefault("health_predictions", {})
    
    return v3_data


def migrate_v3_to_v2(v3_data: Dict[str, Any]) -> Dict[str, Any]:
    """Migrate V3 data back to V2 format (strip V3-only features)."""
    v2_data = v3_data.copy()
    
    # Remove V3-specific fields
    v3_only_fields = [
        "ai_preferences", "biometric_data", "social_connections",
        "ml_insights", "predictive_health", "iot_devices",
        "real_time_health", "activity_tracking", "behavior_analysis",
        "health_predictions"
    ]
    
    for field in v3_only_fields:
        v2_data.pop(field, None)
    
    return v2_data


def migrate_v1_to_v3(v1_data: Dict[str, Any]) -> Dict[str, Any]:
    """Direct migration from V1 to V3."""
    # First migrate V1 to V2, then V2 to V3
    from .v1 import V1EvolutionMixin
    v2_data = V1EvolutionMixin.migrate_to_v2(v1_data)
    return migrate_v2_to_v3(v2_data)


def register_v3_schemas():
    """Register V3 schemas with the global validator."""
    
    # Define V3 schemas
    v3_schemas = {
        "users": UserV3Schema,
        "pets": PetV3Schema,
        # Add more resources as needed
    }
    
    # Define migrations
    migrations_from = {
        "v1": migrate_v1_to_v3,
        "v2": migrate_v2_to_v3,
    }
    
    migrations_to = {
        "v2": migrate_v3_to_v2,
        # v3_to_v1 would go through v2: v3->v2->v1
    }
    
    # Register everything
    add_new_api_version(
        version="v3",
        schemas=v3_schemas,
        migrations_from=migrations_from,
        migrations_to=migrations_to
    )


# Example usage function
def example_v3_usage():
    """Example of how to use V3 schemas."""
    from . import validate_data_by_version, validate_with_smart_fallback
    
    # Register V3 first
    register_v3_schemas()
    
    # Example V3 user data
    v3_user_data = {
        "email": "user@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "ai_preferences": {"language_model": "gpt-4", "automation_level": "high"},
        "biometric_data": {"heart_rate": 72, "steps": 8500},
        "social_connections": ["friend1", "friend2"]
    }
    
    # Validate with V3
    result = validate_data_by_version(v3_user_data, "v3", "users")
    print(f"V3 validation: {result.is_valid}")
    
    # Smart fallback validation (will try V3, V2, V1 in order)
    result = validate_with_smart_fallback(v3_user_data, "users")
    print(f"Smart fallback validation: {result.is_valid}")
    
    return result


if __name__ == "__main__":
    # Demonstrate V3 registration and usage
    example_v3_usage()