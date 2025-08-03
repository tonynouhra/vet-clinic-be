"""
Simple version utilities for dynamic API testing.

Provides helper functions for handling version differences inline
without complex configuration files.
"""

from typing import Dict, Any, List
import uuid


def get_base_url(version: str) -> str:
    """Get base URL for API version."""
    return f"/api/{version}"


def get_pet_endpoint(version: str) -> str:
    """Get pets endpoint for API version."""
    return f"/api/{version}/pets"


def get_user_endpoint(version: str) -> str:
    """Get users endpoint for API version."""
    return f"/api/{version}/users"


def get_appointment_endpoint(version: str) -> str:
    """Get appointments endpoint for API version."""
    return f"/api/{version}/appointments"


def build_pet_create_data(version: str, **overrides) -> Dict[str, Any]:
    """
    Build pet creation data with version-specific fields.
    
    Args:
        version: API version ('v1' or 'v2')
        **overrides: Additional fields to override defaults
        
    Returns:
        Dictionary with pet creation data
    """
    # Base data for all versions
    data = {
        "name": "Buddy",
        "species": "dog",
        "owner_id": str(uuid.uuid4()),
        "breed": "Golden Retriever",
        "gender": "MALE",
        "weight": 65.5,
        "color": "Golden"
    }
    
    # Add V2-specific fields
    if version == "v2":
        data.update({
            "temperament": "Friendly",
            "behavioral_notes": "Good with children",
            "emergency_contact": {
                "name": "John Doe",
                "phone": "555-0123"
            }
        })
    
    # Apply any overrides, but filter out version-specific fields for v1
    if version == "v1":
        # Remove V2-specific fields from overrides for V1
        v2_only_fields = {"temperament", "behavioral_notes", "emergency_contact", "additional_photos"}
        filtered_overrides = {k: v for k, v in overrides.items() if k not in v2_only_fields}
        data.update(filtered_overrides)
    else:
        data.update(overrides)
    return data


def build_user_create_data(version: str, **overrides) -> Dict[str, Any]:
    """
    Build user creation data with version-specific fields.
    
    Args:
        version: API version ('v1' or 'v2')
        **overrides: Additional fields to override defaults
        
    Returns:
        Dictionary with user creation data
    """
    # Base data for all versions
    data = {
        "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
        "password": "TestPassword123!",
        "first_name": "John",
        "last_name": "Doe",
        "phone_number": "555-0123",
        "role": "PET_OWNER"
    }
    
    # Add V2-specific fields
    if version == "v2":
        data.update({
            "address": {
                "street": "123 Main St",
                "city": "Anytown",
                "state": "CA",
                "zip_code": "12345"
            },
            "emergency_contact": {
                "name": "Jane Doe",
                "phone": "555-0456",
                "relationship": "Spouse"
            }
        })
    
    # Apply any overrides
    data.update(overrides)
    return data


def get_expected_response_fields(version: str, resource: str, operation: str) -> List[str]:
    """
    Get expected response fields for a version, resource, and operation.
    
    Args:
        version: API version ('v1' or 'v2')
        resource: Resource type ('pet', 'user', 'appointment')
        operation: Operation type ('create', 'get', 'list')
        
    Returns:
        List of expected field names in response
    """
    base_fields = {
        "pet": ["id", "name", "species", "owner_id", "created_at", "updated_at"],
        "user": ["id", "email", "first_name", "last_name", "role", "created_at", "updated_at"],
        "appointment": ["id", "pet_id", "user_id", "date", "time", "status", "created_at", "updated_at"]
    }
    
    fields = base_fields.get(resource, [])
    
    # Add V2-specific fields
    if version == "v2":
        if resource == "pet":
            fields.extend(["temperament", "behavioral_notes", "emergency_contact", "owner_info"])
        elif resource == "user":
            fields.extend(["address", "emergency_contact", "pet_count"])
        elif resource == "appointment":
            fields.extend(["notes", "veterinarian", "cost"])
    
    return fields


def has_feature(version: str, feature: str) -> bool:
    """
    Check if a feature is available in the specified version.
    
    Args:
        version: API version ('v1' or 'v2')
        feature: Feature name
        
    Returns:
        True if feature is available, False otherwise
    """
    v2_features = {
        "health_records",
        "statistics", 
        "enhanced_filtering",
        "batch_operations",
        "owner_information",
        "additional_photos",
        "behavioral_notes",
        "temperament"
    }
    
    if version == "v1":
        return feature not in v2_features
    elif version == "v2":
        return True
    else:
        return False


def get_health_record_endpoint(version: str, pet_id: str) -> str:
    """Get health records endpoint for a pet (V2 only)."""
    if version != "v2":
        raise ValueError("Health records are only available in V2")
    return f"/api/v2/pets/{pet_id}/health-records"


def build_health_record_data(version: str, **overrides) -> Dict[str, Any]:
    """Build health record data (V2 only)."""
    if version != "v2":
        raise ValueError("Health records are only available in V2")
    
    data = {
        "record_type": "VACCINATION",
        "date": "2024-01-15",
        "description": "Annual vaccination",
        "veterinarian": "Dr. Smith",
        "cost": 75.00,
        "notes": "No adverse reactions"
    }
    
    data.update(overrides)
    return data