"""
Integration tests for TestDataFactory with real configuration and templates.

Tests the complete data generation pipeline using actual configuration files.
"""

import pytest
import uuid
from pathlib import Path

from tests.dynamic.data_factory import TestDataFactory, get_data_factory, reset_data_factory
from tests.dynamic.config_manager import VersionConfigManager, get_config_manager, reset_config_manager
from tests.dynamic.templates import DataTemplateManager, get_template_manager, reset_template_manager


class TestDataFactoryIntegration:
    """Integration tests for TestDataFactory with real configuration."""
    
    def setup_method(self):
        """Set up test fixtures with real configuration."""
        # Reset global instances
        reset_data_factory()
        reset_config_manager()
        reset_template_manager()
        
        # Use real configuration file
        config_path = Path(__file__).parent.parent / "config" / "version_config.yaml"
        self.config_manager = VersionConfigManager(str(config_path))
        self.template_manager = DataTemplateManager(self.config_manager)
        self.factory = TestDataFactory(self.config_manager, self.template_manager)
    
    def test_build_pet_data_v1(self):
        """Test building pet data for v1."""
        data = self.factory.build_pet_data('v1')
        
        # Check required fields are present
        assert 'name' in data
        assert 'species' in data
        assert 'owner_id' in data
        
        # Check v1-specific constraints
        assert 'temperament' not in data  # v2 only field
        assert 'behavioral_notes' not in data  # v2 only field
        assert 'emergency_contact' not in data  # v2 only field
        
        # Validate data types
        assert isinstance(data['name'], str)
        assert isinstance(data['species'], str)
        assert isinstance(data['owner_id'], str)
        
        # Validate UUID format for owner_id
        uuid.UUID(data['owner_id'])
    
    def test_build_pet_data_v2(self):
        """Test building pet data for v2."""
        data = self.factory.build_pet_data('v2')
        
        # Check required fields are present
        assert 'name' in data
        assert 'species' in data
        assert 'owner_id' in data
        
        # Check v2-specific fields are present
        assert 'temperament' in data
        assert 'behavioral_notes' in data
        assert 'emergency_contact' in data
        
        # Validate emergency contact structure
        emergency_contact = data['emergency_contact']
        assert isinstance(emergency_contact, dict)
        assert 'name' in emergency_contact
        assert 'phone' in emergency_contact
        assert 'relationship' in emergency_contact
    
    def test_build_user_data_v1(self):
        """Test building user data for v1."""
        data = self.factory.build_user_data('v1')
        
        # Check required fields
        assert 'email' in data
        assert 'password' in data
        assert 'first_name' in data
        assert 'last_name' in data
        
        # Check v1 constraints
        assert 'address' not in data  # v2 only field
        assert 'emergency_contact' not in data  # v2 only field
        
        # Validate email format
        assert '@' in data['email']
        assert isinstance(data['password'], str)
    
    def test_build_user_data_v2(self):
        """Test building user data for v2."""
        data = self.factory.build_user_data('v2')
        
        # Check required fields
        assert 'email' in data
        assert 'password' in data
        assert 'first_name' in data
        assert 'last_name' in data
        
        # Check v2-specific fields
        assert 'address' in data
        assert 'emergency_contact' in data
        
        # Validate address structure
        address = data['address']
        assert isinstance(address, dict)
        assert 'street' in address
        assert 'city' in address
        assert 'state' in address
        assert 'zip_code' in address
    
    def test_build_appointment_data_v1(self):
        """Test building appointment data for v1."""
        data = self.factory.build_appointment_data('v1')
        
        # Check required fields
        assert 'pet_id' in data
        assert 'user_id' in data
        assert 'date' in data
        assert 'time' in data
        
        # Check v1 constraints
        assert 'notes' not in data  # v2 only field
        assert 'veterinarian' not in data  # v2 only field
        
        # Validate IDs are UUIDs
        uuid.UUID(data['pet_id'])
        uuid.UUID(data['user_id'])
        
        # Validate date format (YYYY-MM-DD)
        date_parts = data['date'].split('-')
        assert len(date_parts) == 3
        assert len(date_parts[0]) == 4  # Year
    
    def test_build_appointment_data_v2(self):
        """Test building appointment data for v2."""
        data = self.factory.build_appointment_data('v2')
        
        # Check required fields
        assert 'pet_id' in data
        assert 'user_id' in data
        assert 'date' in data
        assert 'time' in data
        
        # Check v2-specific fields
        assert 'notes' in data
        assert 'veterinarian' in data
        
        # Validate field types
        assert isinstance(data['notes'], str)
        assert isinstance(data['veterinarian'], str)
    
    def test_build_health_record_data_v2(self):
        """Test building health record data for v2."""
        data = self.factory.build_health_record_data('v2')
        
        # Check required fields
        assert 'record_type' in data
        assert 'date' in data
        assert 'description' in data
        
        # Check optional fields
        assert 'veterinarian' in data
        assert 'cost' in data
        assert 'notes' in data
        
        # Validate field types and values
        assert data['record_type'] in ['VACCINATION', 'CHECKUP', 'SURGERY', 'MEDICATION', 'INJURY', 'ILLNESS']
        assert isinstance(data['cost'], (int, float))
        assert data['cost'] >= 0
    
    def test_build_health_record_data_v1_unsupported(self):
        """Test that health records are not supported in v1."""
        with pytest.raises(Exception, match="Health records not supported in v1"):
            self.factory.build_health_record_data('v1')
    
    def test_data_consistency_across_calls(self):
        """Test that relationship IDs are consistent across multiple calls."""
        # Generate pet data twice
        pet1 = self.factory.build_pet_data('v1')
        pet2 = self.factory.build_pet_data('v1')
        
        # Owner IDs should be the same (cached)
        assert pet1['owner_id'] == pet2['owner_id']
        
        # Generate appointment data
        appointment = self.factory.build_appointment_data('v1')
        
        # Pet and user IDs should be consistent
        assert isinstance(appointment['pet_id'], str)
        assert isinstance(appointment['user_id'], str)
    
    def test_build_related_data_integration(self):
        """Test building related data with real configuration."""
        relationships = {
            'user': 'owner',
            'pet': 'owned_pet',
            'appointment': 'booking'
        }
        
        related_data = self.factory.build_related_data('v2', relationships)
        
        # Check all resources were generated
        assert 'user' in related_data
        assert 'pet' in related_data
        assert 'appointment' in related_data
        
        # Check user data
        user_data = related_data['user']
        assert 'email' in user_data
        assert 'address' in user_data  # v2 specific
        
        # Check pet data
        pet_data = related_data['pet']
        assert 'name' in pet_data
        assert 'temperament' in pet_data  # v2 specific
        
        # Check appointment data
        appointment_data = related_data['appointment']
        assert 'pet_id' in appointment_data
        assert 'user_id' in appointment_data
        assert 'notes' in appointment_data  # v2 specific
    
    def test_validation_with_real_config(self):
        """Test data validation using real configuration."""
        # Generate valid data
        pet_data = self.factory.build_pet_data('v1')
        errors = self.factory.validate_data_against_schema(pet_data, 'v1', 'pet')
        assert errors == []
        
        # Test with invalid data
        invalid_data = {
            'name': 'Buddy',
            # Missing required fields: species, owner_id
            'email': 'invalid-email',  # Invalid format
            'weight': -5.0,  # Invalid value
        }
        errors = self.factory.validate_data_against_schema(invalid_data, 'v1', 'pet')
        assert len(errors) > 0
        assert any('species' in error for error in errors)
        assert any('owner_id' in error for error in errors)
        assert any('email' in error for error in errors)
        assert any('weight' in error for error in errors)
    
    def test_expected_response_fields_real_config(self):
        """Test getting expected response fields with real configuration."""
        # Test pet response fields for v1
        v1_fields = self.factory.get_expected_response_fields('v1', 'pet')
        expected_v1_fields = ['id', 'name', 'species', 'breed', 'owner_id', 'gender', 'weight', 'color', 'created_at', 'updated_at']
        for field in expected_v1_fields:
            assert field in v1_fields
        
        # Test pet response fields for v2
        v2_fields = self.factory.get_expected_response_fields('v2', 'pet')
        expected_v2_fields = ['temperament', 'behavioral_notes', 'emergency_contact', 'owner_info', 'additional_photos']
        for field in expected_v2_fields:
            assert field in v2_fields
        
        # v2 should have all v1 fields plus additional ones
        assert len(v2_fields) > len(v1_fields)
    
    def test_update_data_generation(self):
        """Test generating update data."""
        # Test pet update data
        pet_update = self.factory.build_update_data('v2', 'pet', name='Updated Name')
        
        assert 'name' in pet_update
        assert pet_update['name'] == 'Updated Name'
        
        # Should include optional fields that can be updated
        optional_fields = self.config_manager.get_optional_fields('v2', 'pet_create')
        for field in optional_fields:
            if field in pet_update:
                assert pet_update[field] is not None
    
    def test_template_fallback_integration(self):
        """Test that template fallback works with real configuration."""
        # This should work even if templates fail
        data = self.factory.build_pet_data('v1', use_template=False)
        
        assert 'name' in data
        assert 'species' in data
        assert 'owner_id' in data
        
        # Validate against schema
        errors = self.factory.validate_data_against_schema(data, 'v1', 'pet')
        assert errors == []
    
    def test_field_overrides_integration(self):
        """Test field overrides with real configuration."""
        custom_name = "CustomPetName"
        custom_species = "custom_species"
        
        data = self.factory.build_pet_data('v1', name=custom_name, species=custom_species)
        
        assert data['name'] == custom_name
        assert data['species'] == custom_species
        
        # Other fields should still be generated
        assert 'owner_id' in data
        assert isinstance(data['owner_id'], str)
    
    def test_version_specific_features(self):
        """Test that version-specific features are handled correctly."""
        # v1 should not have health records feature
        assert not self.config_manager.get_feature_availability('v1', 'health_records')
        
        # v2 should have health records feature
        assert self.config_manager.get_feature_availability('v2', 'health_records')
        
        # Test other v2 features
        v2_features = ['statistics', 'enhanced_filtering', 'batch_operations']
        for feature in v2_features:
            assert self.config_manager.get_feature_availability('v2', feature)
            assert not self.config_manager.get_feature_availability('v1', feature)


class TestGlobalFactoryIntegration:
    """Test global factory functions with real configuration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        reset_data_factory()
        reset_config_manager()
        reset_template_manager()
    
    def teardown_method(self):
        """Clean up after tests."""
        reset_data_factory()
        reset_config_manager()
        reset_template_manager()
    
    def test_global_factory_with_real_config(self):
        """Test global factory functions work with real configuration."""
        factory = get_data_factory()
        
        # Should be able to generate data
        pet_data = factory.build_pet_data('v1')
        assert 'name' in pet_data
        assert 'species' in pet_data
        
        # Should use real configuration
        versions = factory.config_manager.get_supported_versions()
        assert 'v1' in versions
        assert 'v2' in versions
    
    def test_factory_singleton_behavior(self):
        """Test that global factory maintains singleton behavior."""
        factory1 = get_data_factory()
        factory2 = get_data_factory()
        
        assert factory1 is factory2
        
        # Should maintain relationship cache across calls
        pet1 = factory1.build_pet_data('v1')
        pet2 = factory2.build_pet_data('v1')
        
        assert pet1['owner_id'] == pet2['owner_id']