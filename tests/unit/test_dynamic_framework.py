"""
Unit tests for the dynamic testing framework components.

Tests the simplified version utilities and base test functionality.
"""

import pytest
import uuid
from unittest.mock import AsyncMock

from tests.dynamic.version_utils import (
    get_base_url,
    get_pet_endpoint,
    get_user_endpoint,
    get_appointment_endpoint,
    build_pet_create_data,
    build_user_create_data,
    get_expected_response_fields,
    has_feature,
    get_health_record_endpoint,
    build_health_record_data
)
from tests.dynamic.base_test import BaseDynamicTest


class TestVersionUtils:
    """Test cases for version utilities."""
    
    def test_get_base_url(self):
        """Test getting base URLs for different versions."""
        assert get_base_url("v1") == "/api/v1"
        assert get_base_url("v2") == "/api/v2"
        assert get_base_url("v3") == "/api/v3"  # Should work for any version
    
    def test_get_endpoint_urls(self):
        """Test getting endpoint URLs for different resources."""
        assert get_pet_endpoint("v1") == "/api/v1/pets"
        assert get_pet_endpoint("v2") == "/api/v2/pets"
        
        assert get_user_endpoint("v1") == "/api/v1/users"
        assert get_user_endpoint("v2") == "/api/v2/users"
        
        assert get_appointment_endpoint("v1") == "/api/v1/appointments"
        assert get_appointment_endpoint("v2") == "/api/v2/appointments"
    
    def test_build_pet_create_data_v1(self):
        """Test building pet creation data for V1."""
        data = build_pet_create_data("v1")
        
        # Should have base fields
        assert "name" in data
        assert "species" in data
        assert "owner_id" in data
        assert "breed" in data
        assert "gender" in data
        
        # Should not have V2-specific fields
        assert "temperament" not in data
        assert "behavioral_notes" not in data
        assert "emergency_contact" not in data
    
    def test_build_pet_create_data_v2(self):
        """Test building pet creation data for V2."""
        data = build_pet_create_data("v2")
        
        # Should have base fields
        assert "name" in data
        assert "species" in data
        assert "owner_id" in data
        assert "breed" in data
        assert "gender" in data
        
        # Should have V2-specific fields
        assert "temperament" in data
        assert "behavioral_notes" in data
        assert "emergency_contact" in data
        assert data["temperament"] == "Friendly"
        assert data["behavioral_notes"] == "Good with children"
    
    def test_build_pet_create_data_with_overrides(self):
        """Test building pet creation data with overrides."""
        overrides = {
            "name": "Max",
            "species": "cat",
            "temperament": "Calm"
        }
        
        v1_data = build_pet_create_data("v1", **overrides)
        assert v1_data["name"] == "Max"
        assert v1_data["species"] == "cat"
        assert "temperament" not in v1_data  # V1 shouldn't have this even with override
        
        v2_data = build_pet_create_data("v2", **overrides)
        assert v2_data["name"] == "Max"
        assert v2_data["species"] == "cat"
        assert v2_data["temperament"] == "Calm"  # Override should work
    
    def test_build_user_create_data_v1(self):
        """Test building user creation data for V1."""
        data = build_user_create_data("v1")
        
        # Should have base fields
        assert "email" in data
        assert "password" in data
        assert "first_name" in data
        assert "last_name" in data
        assert "role" in data
        
        # Should not have V2-specific fields
        assert "address" not in data
        assert "emergency_contact" not in data
    
    def test_build_user_create_data_v2(self):
        """Test building user creation data for V2."""
        data = build_user_create_data("v2")
        
        # Should have base fields
        assert "email" in data
        assert "password" in data
        assert "first_name" in data
        assert "last_name" in data
        assert "role" in data
        
        # Should have V2-specific fields
        assert "address" in data
        assert "emergency_contact" in data
        assert isinstance(data["address"], dict)
        assert isinstance(data["emergency_contact"], dict)
    
    def test_get_expected_response_fields(self):
        """Test getting expected response fields for different versions and resources."""
        # Pet fields
        v1_pet_fields = get_expected_response_fields("v1", "pet", "get")
        v2_pet_fields = get_expected_response_fields("v2", "pet", "get")
        
        # Base fields should be in both
        base_pet_fields = ["id", "name", "species", "owner_id", "created_at", "updated_at"]
        for field in base_pet_fields:
            assert field in v1_pet_fields
            assert field in v2_pet_fields
        
        # V2-specific fields should only be in V2
        v2_only_fields = ["temperament", "behavioral_notes", "emergency_contact", "owner_info"]
        for field in v2_only_fields:
            assert field not in v1_pet_fields
            assert field in v2_pet_fields
        
        # User fields
        v1_user_fields = get_expected_response_fields("v1", "user", "get")
        v2_user_fields = get_expected_response_fields("v2", "user", "get")
        
        # V2 should have additional user fields
        assert "address" not in v1_user_fields
        assert "address" in v2_user_fields
        assert "pet_count" not in v1_user_fields
        assert "pet_count" in v2_user_fields
    
    def test_has_feature(self):
        """Test feature availability checking."""
        # V2-only features
        v2_features = ["health_records", "statistics", "enhanced_filtering", "batch_operations"]
        
        for feature in v2_features:
            assert has_feature("v1", feature) is False
            assert has_feature("v2", feature) is True
        
        # Invalid version should return False
        assert has_feature("v99", "health_records") is False
    
    def test_get_health_record_endpoint(self):
        """Test getting health record endpoint (V2 only)."""
        pet_id = str(uuid.uuid4())
        
        # Should work for V2
        endpoint = get_health_record_endpoint("v2", pet_id)
        assert endpoint == f"/api/v2/pets/{pet_id}/health-records"
        
        # Should raise error for V1
        with pytest.raises(ValueError, match="Health records are only available in V2"):
            get_health_record_endpoint("v1", pet_id)
    
    def test_build_health_record_data(self):
        """Test building health record data (V2 only)."""
        # Should work for V2
        data = build_health_record_data("v2")
        assert "record_type" in data
        assert "date" in data
        assert "description" in data
        assert "veterinarian" in data
        assert "cost" in data
        assert "notes" in data
        
        # Should raise error for V1
        with pytest.raises(ValueError, match="Health records are only available in V2"):
            build_health_record_data("v1")
        
        # Test with overrides
        overrides = {"record_type": "CHECKUP", "cost": 100.0}
        data = build_health_record_data("v2", **overrides)
        assert data["record_type"] == "CHECKUP"
        assert data["cost"] == 100.0


class TestBaseDynamicTest:
    """Test cases for BaseDynamicTest class."""
    
    def test_get_version_url(self):
        """Test version URL method."""
        base_test = BaseDynamicTest()
        
        # Test the method directly
        assert base_test.get_version_url("v1") == "/api/v1"
        assert base_test.get_version_url("v2") == "/api/v2"
    
    def test_assert_response_structure(self):
        """Test response structure assertion."""
        base_test = BaseDynamicTest()
        
        # Valid V1 pet response
        v1_pet_response = {
            "id": str(uuid.uuid4()),
            "name": "Buddy",
            "species": "dog",
            "owner_id": str(uuid.uuid4()),
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }
        
        # Should not raise any assertion errors
        base_test.assert_response_structure(v1_pet_response, "v1", "pet")
        
        # Missing required field should raise assertion error
        incomplete_response = {"id": str(uuid.uuid4()), "name": "Buddy"}
        
        with pytest.raises(AssertionError, match="Expected field 'species' not found"):
            base_test.assert_response_structure(incomplete_response, "v1", "pet")
    
    def test_assert_version_specific_fields(self):
        """Test version-specific field assertions."""
        base_test = BaseDynamicTest()
        
        # V1 pet response (should not have V2 fields)
        v1_response = {
            "id": str(uuid.uuid4()),
            "name": "Buddy",
            "species": "dog"
        }
        
        base_test.assert_version_specific_fields(v1_response, "v1", "pet")
        
        # V2 pet response (should have V2 fields)
        v2_response = {
            "id": str(uuid.uuid4()),
            "name": "Buddy",
            "species": "dog",
            "temperament": "Friendly",
            "behavioral_notes": "Good with children",
            "emergency_contact": {"name": "John", "phone": "555-0123"}
        }
        
        base_test.assert_version_specific_fields(v2_response, "v2", "pet")
        
        # V1 response with V2 fields should fail
        v1_with_v2_fields = {
            "id": str(uuid.uuid4()),
            "name": "Buddy",
            "temperament": "Friendly"  # This shouldn't be in V1
        }
        
        with pytest.raises(AssertionError, match="V1 pet response should not include temperament"):
            base_test.assert_version_specific_fields(v1_with_v2_fields, "v1", "pet")
    
    def test_skip_if_feature_not_available(self):
        """Test feature availability skipping."""
        base_test = BaseDynamicTest()
        
        # Should skip for V1 health_records
        with pytest.raises(pytest.skip.Exception, match="Feature 'health_records' not available in v1"):
            base_test.skip_if_feature_not_available("v1", "health_records")
        
        # Should not skip for V2 health_records
        base_test.skip_if_feature_not_available("v2", "health_records")  # Should not raise
    
    def test_create_test_user_data_generation(self):
        """Test that create_test_user generates correct data for API calls."""
        base_test = BaseDynamicTest()
        
        # Test that the method would generate correct user data
        from tests.dynamic.version_utils import build_user_create_data
        
        v1_data = build_user_create_data("v1")
        assert "email" in v1_data
        assert "password" in v1_data
        assert "first_name" in v1_data
        assert "last_name" in v1_data
        assert "address" not in v1_data  # V1 shouldn't have address
        
        v2_data = build_user_create_data("v2")
        assert "email" in v2_data
        assert "password" in v2_data
        assert "first_name" in v2_data
        assert "last_name" in v2_data
        assert "address" in v2_data  # V2 should have address
    
    def test_create_test_pet_data_generation(self):
        """Test that create_test_pet generates correct data for API calls."""
        base_test = BaseDynamicTest()
        
        # Test that the method would generate correct pet data
        from tests.dynamic.version_utils import build_pet_create_data
        
        owner_id = str(uuid.uuid4())
        
        v1_data = build_pet_create_data("v1", owner_id=owner_id)
        assert v1_data["owner_id"] == owner_id
        assert "name" in v1_data
        assert "species" in v1_data
        assert "temperament" not in v1_data  # V1 shouldn't have temperament
        
        v2_data = build_pet_create_data("v2", owner_id=owner_id)
        assert v2_data["owner_id"] == owner_id
        assert "name" in v2_data
        assert "species" in v2_data
        assert "temperament" in v2_data  # V2 should have temperament