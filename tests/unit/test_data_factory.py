"""
Unit tests for the TestDataFactory class.

Tests data generation, template integration, and validation functionality.
"""

import pytest
import uuid
from unittest.mock import Mock, patch

from tests.dynamic.data_factory import TestDataFactory, TestDataGenerationError, get_data_factory, reset_data_factory
from tests.dynamic.config_manager import VersionConfigManager, ConfigurationError
from tests.dynamic.templates import DataTemplateManager, TemplateError


class TestTestDataFactory:
    """Test cases for TestDataFactory class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Reset global instances
        reset_data_factory()
        
        # Create mock config manager
        self.mock_config = Mock(spec=VersionConfigManager)
        self.mock_template = Mock(spec=DataTemplateManager)
        
        # Set up default mock responses
        self.mock_config.get_default_values.return_value = {
            'name': 'Buddy',
            'species': 'dog',
            'owner_id': str(uuid.uuid4())
        }
        self.mock_config.get_required_fields.return_value = ['name', 'species', 'owner_id']
        self.mock_config.get_optional_fields.return_value = ['breed', 'weight']
        self.mock_config.get_schema_fields.return_value = ['name', 'species', 'owner_id', 'breed', 'weight']
        self.mock_config.get_feature_availability.return_value = True
        
        self.factory = TestDataFactory(self.mock_config, self.mock_template)
    
    def test_initialization(self):
        """Test factory initialization."""
        assert self.factory.config_manager == self.mock_config
        assert self.factory.template_manager == self.mock_template
        assert isinstance(self.factory._field_generators, dict)
        assert isinstance(self.factory._relationship_cache, dict)
    
    def test_build_pet_data_with_template(self):
        """Test pet data generation using templates."""
        expected_data = {
            'name': 'Max',
            'species': 'dog',
            'breed': 'Labrador',
            'owner_id': str(uuid.uuid4())
        }
        self.mock_template.generate_from_template.return_value = expected_data
        
        result = self.factory.build_pet_data('v1', name='Max')
        
        self.mock_template.generate_from_template.assert_called_once_with(
            'pet', 'create', 'v1', name='Max'
        )
        assert result == expected_data
    
    def test_build_pet_data_without_template(self):
        """Test pet data generation without templates."""
        result = self.factory.build_pet_data('v1', use_template=False, name='Buddy')
        
        assert result['name'] == 'Buddy'
        assert result['species'] == 'dog'
        assert 'owner_id' in result
        self.mock_template.generate_from_template.assert_not_called()
    
    def test_build_pet_data_template_fallback(self):
        """Test fallback to direct generation when template fails."""
        self.mock_template.generate_from_template.side_effect = TemplateError("Template failed")
        
        result = self.factory.build_pet_data('v1', name='Buddy')
        
        assert result['name'] == 'Buddy'
        assert result['species'] == 'dog'
        assert 'owner_id' in result
    
    def test_build_user_data_with_template(self):
        """Test user data generation using templates."""
        expected_data = {
            'email': 'test@example.com',
            'first_name': 'John',
            'last_name': 'Doe'
        }
        self.mock_template.generate_from_template.return_value = expected_data
        
        result = self.factory.build_user_data('v2', email='test@example.com')
        
        self.mock_template.generate_from_template.assert_called_once_with(
            'user', 'create', 'v2', email='test@example.com'
        )
        assert result == expected_data
    
    def test_build_appointment_data_with_template(self):
        """Test appointment data generation using templates."""
        expected_data = {
            'pet_id': str(uuid.uuid4()),
            'user_id': str(uuid.uuid4()),
            'date': '2024-01-15',
            'time': '10:00'
        }
        self.mock_template.generate_from_template.return_value = expected_data
        
        result = self.factory.build_appointment_data('v1', date='2024-01-15')
        
        self.mock_template.generate_from_template.assert_called_once_with(
            'appointment', 'create', 'v1', date='2024-01-15'
        )
        assert result == expected_data
    
    def test_build_health_record_data_supported_version(self):
        """Test health record data generation for supported version."""
        self.mock_config.get_feature_availability.return_value = True
        expected_data = {
            'record_type': 'VACCINATION',
            'date': '2024-01-15',
            'description': 'Annual vaccination'
        }
        self.mock_template.generate_from_template.return_value = expected_data
        
        result = self.factory.build_health_record_data('v2')
        
        self.mock_config.get_feature_availability.assert_called_with('v2', 'health_records')
        assert result == expected_data
    
    def test_build_health_record_data_unsupported_version(self):
        """Test health record data generation for unsupported version."""
        self.mock_config.get_feature_availability.return_value = False
        
        with pytest.raises(TestDataGenerationError, match="Health records not supported in v1"):
            self.factory.build_health_record_data('v1')
    
    def test_get_expected_response_fields(self):
        """Test getting expected response fields."""
        expected_fields = ['id', 'name', 'species', 'created_at']
        self.mock_config.get_schema_fields.return_value = expected_fields
        
        result = self.factory.get_expected_response_fields('v1', 'pet')
        
        self.mock_config.get_schema_fields.assert_called_once_with('v1', 'pet_response')
        assert result == expected_fields
    
    def test_get_expected_response_fields_config_error(self):
        """Test getting expected response fields when config error occurs."""
        self.mock_config.get_schema_fields.side_effect = ConfigurationError("Schema not found")
        
        result = self.factory.get_expected_response_fields('v1', 'pet')
        
        assert result == []
    
    def test_build_update_data(self):
        """Test building update data."""
        self.mock_config.get_optional_fields.return_value = ['breed', 'weight', 'color']
        
        # Mock the _build_resource_data method
        with patch.object(self.factory, '_build_resource_data') as mock_build:
            mock_build.return_value = {
                'name': 'Buddy',
                'breed': 'Labrador',
                'weight': 25.5,
                'color': 'Golden'
            }
            
            result = self.factory.build_update_data('v1', 'pet', weight=30.0)
            
            assert 'weight' in result
            assert result['weight'] == 30.0
            assert 'breed' in result
            assert 'color' in result
    
    def test_validate_data_against_schema_valid(self):
        """Test data validation with valid data."""
        data = {
            'name': 'Buddy',
            'species': 'dog',
            'owner_id': str(uuid.uuid4()),
            'email': 'test@example.com',
            'weight': 25.5,
            'cost': 100.0,
            'date': '2024-01-15'
        }
        
        errors = self.factory.validate_data_against_schema(data, 'v1', 'pet')
        
        assert errors == []
    
    def test_validate_data_against_schema_missing_required(self):
        """Test data validation with missing required fields."""
        data = {
            'name': 'Buddy',
            # Missing 'species' and 'owner_id'
        }
        
        errors = self.factory.validate_data_against_schema(data, 'v1', 'pet')
        
        assert len(errors) >= 2
        assert any('species' in error for error in errors)
        assert any('owner_id' in error for error in errors)
    
    def test_validate_data_against_schema_invalid_fields(self):
        """Test data validation with invalid field values."""
        data = {
            'name': 'Buddy',
            'species': 'dog',
            'owner_id': str(uuid.uuid4()),
            'email': 'invalid-email',  # Invalid email
            'weight': -5.0,  # Invalid weight
            'cost': -10.0,  # Invalid cost
            'date': 'invalid-date'  # Invalid date
        }
        
        errors = self.factory.validate_data_against_schema(data, 'v1', 'pet')
        
        assert len(errors) >= 4
        assert any('email' in error for error in errors)
        assert any('weight' in error for error in errors)
        assert any('cost' in error for error in errors)
        assert any('date' in error for error in errors)
    
    def test_validate_data_v2_complex_fields(self):
        """Test validation of v2 complex fields."""
        data = {
            'name': 'Buddy',
            'species': 'dog',
            'owner_id': str(uuid.uuid4()),
            'emergency_contact': {
                'name': 'John Doe',
                'phone': '555-0123'
            },
            'address': {
                'street': '123 Main St',
                'city': 'Anytown',
                'state': 'CA',
                'zip_code': '12345'
            }
        }
        
        errors = self.factory.validate_data_against_schema(data, 'v2', 'user')
        
        assert errors == []
    
    def test_validate_data_v2_invalid_complex_fields(self):
        """Test validation of invalid v2 complex fields."""
        data = {
            'name': 'Buddy',
            'species': 'dog',
            'owner_id': str(uuid.uuid4()),
            'emergency_contact': {
                # Missing 'name' and 'phone'
            },
            'address': {
                'street': '123 Main St',
                # Missing other required fields
            }
        }
        
        errors = self.factory.validate_data_against_schema(data, 'v2', 'user')
        
        assert len(errors) >= 5  # Missing emergency contact fields + address fields
    
    def test_clear_relationship_cache(self):
        """Test clearing relationship cache."""
        # Add some data to cache
        self.factory._relationship_cache['test_key'] = 'test_value'
        
        self.factory.clear_relationship_cache()
        
        assert self.factory._relationship_cache == {}
        self.mock_template.clear_relationship_cache.assert_called_once()
    
    def test_set_relationship_id(self):
        """Test setting relationship ID."""
        test_id = str(uuid.uuid4())
        
        # Mock field generator with set_id method
        mock_generator = Mock()
        mock_generator.set_id = Mock()
        self.mock_template.get_field_generator.return_value = mock_generator
        
        self.factory.set_relationship_id('owner_id', 'v1', 'pet', test_id)
        
        cache_key = 'v1_pet_owner_id'
        assert self.factory._relationship_cache[cache_key] == test_id
        mock_generator.set_id.assert_called_once_with(test_id)
    
    def test_build_related_data(self):
        """Test building related data with consistent relationships."""
        # Mock the individual build methods
        with patch.object(self.factory, 'build_user_data') as mock_user, \
             patch.object(self.factory, 'build_pet_data') as mock_pet, \
             patch.object(self.factory, 'build_appointment_data') as mock_appointment:
            
            user_data = {'id': 'user-123', 'email': 'test@example.com'}
            pet_data = {'id': 'pet-456', 'name': 'Buddy', 'owner_id': 'user-123'}
            appointment_data = {'id': 'appt-789', 'pet_id': 'pet-456', 'user_id': 'user-123'}
            
            mock_user.return_value = user_data
            mock_pet.return_value = pet_data
            mock_appointment.return_value = appointment_data
            
            relationships = {
                'user': 'owner',
                'pet': 'owned_pet',
                'appointment': 'booking'
            }
            
            result = self.factory.build_related_data('v2', relationships, user_email='test@example.com')
            
            assert result['user'] == user_data
            assert result['pet'] == pet_data
            assert result['appointment'] == appointment_data
            
            # Verify user data was built with override
            mock_user.assert_called_once_with('v2', email='test@example.com')
            
            # Verify pet data was built with owner_id
            mock_pet.assert_called_once_with('v2', owner_id='user-123')
            
            # Verify appointment data was built with both IDs
            mock_appointment.assert_called_once_with('v2', pet_id='pet-456', user_id='user-123')


class TestGlobalDataFactory:
    """Test cases for global data factory functions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        reset_data_factory()
    
    def teardown_method(self):
        """Clean up after tests."""
        reset_data_factory()
    
    def test_get_data_factory_singleton(self):
        """Test that get_data_factory returns singleton instance."""
        factory1 = get_data_factory()
        factory2 = get_data_factory()
        
        assert factory1 is factory2
        assert isinstance(factory1, TestDataFactory)
    
    def test_get_data_factory_with_custom_managers(self):
        """Test get_data_factory with custom managers."""
        mock_config = Mock(spec=VersionConfigManager)
        mock_template = Mock(spec=DataTemplateManager)
        
        factory = get_data_factory(mock_config, mock_template)
        
        assert factory.config_manager == mock_config
        assert factory.template_manager == mock_template
    
    def test_reset_data_factory(self):
        """Test resetting global data factory."""
        factory1 = get_data_factory()
        reset_data_factory()
        factory2 = get_data_factory()
        
        assert factory1 is not factory2


class TestFieldGenerators:
    """Test cases for field generator methods."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.factory = TestDataFactory()
    
    def test_generate_email(self):
        """Test email generation."""
        email = self.factory._generate_email()
        
        assert isinstance(email, str)
        assert '@' in email
        assert email.endswith(('.com', '.org', '.net'))
    
    def test_generate_phone_number(self):
        """Test phone number generation."""
        phone = self.factory._generate_phone_number()
        
        assert isinstance(phone, str)
        assert phone.startswith('555-')
        assert len(phone) == 8  # Format: 555-XXXX
    
    def test_generate_pet_name(self):
        """Test pet name generation."""
        name = self.factory._generate_pet_name()
        
        assert isinstance(name, str)
        assert len(name) > 0
    
    def test_generate_weight(self):
        """Test weight generation."""
        weight = self.factory._generate_weight()
        
        assert isinstance(weight, float)
        assert 5.0 <= weight <= 100.0
    
    def test_generate_cost(self):
        """Test cost generation."""
        cost = self.factory._generate_cost()
        
        assert isinstance(cost, float)
        assert 25.0 <= cost <= 500.0
        assert len(str(cost).split('.')[-1]) <= 2  # Max 2 decimal places
    
    def test_generate_emergency_contact(self):
        """Test emergency contact generation."""
        contact = self.factory._generate_emergency_contact()
        
        assert isinstance(contact, dict)
        assert 'name' in contact
        assert 'phone' in contact
        assert 'relationship' in contact
        assert isinstance(contact['name'], str)
        assert isinstance(contact['phone'], str)
        assert contact['relationship'] in ['Spouse', 'Parent', 'Sibling', 'Friend']
    
    def test_generate_address(self):
        """Test address generation."""
        address = self.factory._generate_address()
        
        assert isinstance(address, dict)
        required_fields = ['street', 'city', 'state', 'zip_code']
        for field in required_fields:
            assert field in address
            assert isinstance(address[field], str)
            assert len(address[field]) > 0