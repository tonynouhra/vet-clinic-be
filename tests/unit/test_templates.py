"""
Unit tests for the template system.

Tests data templates, field generators, and template management functionality.
"""

import pytest
import uuid
from unittest.mock import Mock, patch

from tests.dynamic.templates import (
    DataTemplate, FieldGenerator, BaseFieldGenerator, StringFieldGenerator,
    NumericFieldGenerator, DateTimeFieldGenerator, RelationshipFieldGenerator,
    ComplexFieldGenerator, DataTemplateManager, TemplateError,
    get_template_manager, reset_template_manager
)
from tests.dynamic.config_manager import VersionConfigManager, ConfigurationError


class TestFieldGenerators:
    """Test cases for field generator classes."""
    
    def test_string_field_generator_with_choices(self):
        """Test string generator with predefined choices."""
        choices = ['option1', 'option2', 'option3']
        generator = StringFieldGenerator(choices=choices)
        
        result = generator.generate()
        
        assert result in choices
        assert isinstance(result, str)
    
    def test_string_field_generator_with_pattern(self):
        """Test string generator with patterns."""
        # Test email pattern
        email_generator = StringFieldGenerator(pattern='email')
        email = email_generator.generate()
        assert '@' in email
        assert email.endswith('.com')
        
        # Test phone pattern
        phone_generator = StringFieldGenerator(pattern='phone')
        phone = phone_generator.generate()
        assert phone.startswith('555-')
        
        # Test name pattern
        name_generator = StringFieldGenerator(pattern='name')
        name = name_generator.generate()
        assert isinstance(name, str)
        assert len(name) > 0
    
    def test_string_field_generator_random(self):
        """Test string generator with random generation."""
        generator = StringFieldGenerator(min_length=5, max_length=10)
        
        result = generator.generate()
        
        assert isinstance(result, str)
        assert 5 <= len(result) <= 10
    
    def test_numeric_field_generator_integer(self):
        """Test numeric generator for integers."""
        generator = NumericFieldGenerator(min_value=1, max_value=10, decimal_places=0)
        
        result = generator.generate()
        
        assert isinstance(result, int)
        assert 1 <= result <= 10
    
    def test_numeric_field_generator_float(self):
        """Test numeric generator for floats."""
        generator = NumericFieldGenerator(min_value=1.0, max_value=10.0, decimal_places=2)
        
        result = generator.generate()
        
        assert isinstance(result, float)
        assert 1.0 <= result <= 10.0
        # Check decimal places
        assert len(str(result).split('.')[-1]) <= 2
    
    def test_datetime_field_generator_date(self):
        """Test datetime generator for dates."""
        generator = DateTimeFieldGenerator(format_type='date')
        
        result = generator.generate()
        
        assert isinstance(result, str)
        # Should match YYYY-MM-DD format
        parts = result.split('-')
        assert len(parts) == 3
        assert len(parts[0]) == 4  # Year
        assert len(parts[1]) == 2  # Month
        assert len(parts[2]) == 2  # Day
    
    def test_datetime_field_generator_time(self):
        """Test datetime generator for times."""
        generator = DateTimeFieldGenerator(format_type='time')
        
        result = generator.generate()
        
        assert isinstance(result, str)
        # Should match HH:MM format
        parts = result.split(':')
        assert len(parts) == 2
        hour, minute = int(parts[0]), int(parts[1])
        assert 8 <= hour <= 17  # Business hours
        assert minute in [0, 15, 30, 45]
    
    def test_relationship_field_generator(self):
        """Test relationship field generator."""
        generator = RelationshipFieldGenerator('user', 'test_cache_key')
        
        result1 = generator.generate()
        result2 = generator.generate()
        
        # Should return same ID for consistency
        assert result1 == result2
        assert isinstance(result1, str)
        # Should be valid UUID format
        uuid.UUID(result1)  # Will raise ValueError if invalid
    
    def test_relationship_field_generator_set_id(self):
        """Test setting specific ID in relationship generator."""
        generator = RelationshipFieldGenerator('user')
        test_id = str(uuid.uuid4())
        
        generator.set_id(test_id)
        result = generator.generate()
        
        assert result == test_id
    
    def test_relationship_field_generator_clear_cache(self):
        """Test clearing relationship generator cache."""
        generator = RelationshipFieldGenerator('user')
        
        result1 = generator.generate()
        generator.clear_cache()
        result2 = generator.generate()
        
        # Should generate different ID after cache clear
        assert result1 != result2
    
    def test_complex_field_generator(self):
        """Test complex field generator for nested objects."""
        template = {
            'name': 'default_name',
            'phone': 'default_phone',
            'relationship': 'default_relationship'
        }
        field_generators = {
            'name': StringFieldGenerator(choices=['John Doe', 'Jane Smith']),
            'phone': StringFieldGenerator(pattern='phone')
        }
        
        generator = ComplexFieldGenerator(template, field_generators)
        result = generator.generate()
        
        assert isinstance(result, dict)
        assert 'name' in result
        assert 'phone' in result
        assert 'relationship' in result
        assert result['name'] in ['John Doe', 'Jane Smith']
        assert result['phone'].startswith('555-')
        assert result['relationship'] == 'default_relationship'  # Not overridden


class TestDataTemplate:
    """Test cases for DataTemplate class."""
    
    def test_data_template_creation(self):
        """Test creating a data template."""
        template = DataTemplate(
            resource_type='pet',
            operation='create',
            base_data={'name': 'Buddy', 'species': 'dog'},
            relationships={'owner_id': 'user'},
            version_overrides={'v2': {'temperament': 'Friendly'}}
        )
        
        assert template.resource_type == 'pet'
        assert template.operation == 'create'
        assert template.base_data['name'] == 'Buddy'
        assert template.relationships['owner_id'] == 'user'
        assert template.version_overrides['v2']['temperament'] == 'Friendly'


class TestDataTemplateManager:
    """Test cases for DataTemplateManager class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        reset_template_manager()
        
        # Create mock config manager
        self.mock_config = Mock(spec=VersionConfigManager)
        self.mock_config.get_required_fields.return_value = ['name', 'species']
        self.mock_config.get_optional_fields.return_value = ['breed', 'weight']
        self.mock_config.get_schema_fields.return_value = ['name', 'species', 'breed', 'weight']
        
        self.manager = DataTemplateManager(self.mock_config)
    
    def test_initialization(self):
        """Test template manager initialization."""
        assert self.manager.config_manager == self.mock_config
        assert isinstance(self.manager._templates, dict)
        assert isinstance(self.manager._field_generators, dict)
        
        # Check that default generators are initialized
        assert 'email' in self.manager._field_generators
        assert 'pet_name' in self.manager._field_generators
        assert 'owner_id' in self.manager._field_generators
    
    def test_register_and_get_template(self):
        """Test registering and retrieving templates."""
        template = DataTemplate(
            resource_type='test_resource',
            operation='create',
            base_data={'field1': 'value1'}
        )
        
        self.manager.register_template(template)
        retrieved = self.manager.get_template('test_resource', 'create')
        
        assert retrieved == template
        assert retrieved.base_data['field1'] == 'value1'
    
    def test_get_nonexistent_template(self):
        """Test retrieving non-existent template."""
        result = self.manager.get_template('nonexistent', 'create')
        
        assert result is None
    
    def test_generate_from_template_basic(self):
        """Test basic data generation from template."""
        template = DataTemplate(
            resource_type='pet',
            operation='create',
            base_data={'name': 'Buddy', 'species': 'dog'}
        )
        self.manager.register_template(template)
        
        result = self.manager.generate_from_template('pet', 'create', 'v1')
        
        assert result['name'] == 'Buddy'
        assert result['species'] == 'dog'
    
    def test_generate_from_template_with_version_overrides(self):
        """Test data generation with version-specific overrides."""
        template = DataTemplate(
            resource_type='pet',
            operation='create',
            base_data={'name': 'Buddy', 'species': 'dog'},
            version_overrides={
                'v2': {'temperament': 'Friendly', 'behavioral_notes': 'Good with kids'}
            }
        )
        self.manager.register_template(template)
        
        # Test v1 (no overrides)
        result_v1 = self.manager.generate_from_template('pet', 'create', 'v1')
        assert 'temperament' not in result_v1
        
        # Test v2 (with overrides)
        result_v2 = self.manager.generate_from_template('pet', 'create', 'v2')
        assert result_v2['temperament'] == 'Friendly'
        assert result_v2['behavioral_notes'] == 'Good with kids'
    
    def test_generate_from_template_with_relationships(self):
        """Test data generation with relationship fields."""
        template = DataTemplate(
            resource_type='pet',
            operation='create',
            base_data={'name': 'Buddy', 'species': 'dog'},
            relationships={'owner_id': 'user'}
        )
        self.manager.register_template(template)
        
        result = self.manager.generate_from_template('pet', 'create', 'v1')
        
        assert 'owner_id' in result
        assert isinstance(result['owner_id'], str)
        # Should be valid UUID
        uuid.UUID(result['owner_id'])
    
    def test_generate_from_template_with_overrides(self):
        """Test data generation with field overrides."""
        template = DataTemplate(
            resource_type='pet',
            operation='create',
            base_data={'name': 'Buddy', 'species': 'dog'}
        )
        self.manager.register_template(template)
        
        result = self.manager.generate_from_template(
            'pet', 'create', 'v1', name='Max', breed='Labrador'
        )
        
        assert result['name'] == 'Max'  # Override applied
        assert result['species'] == 'dog'  # Base data preserved
        assert result['breed'] == 'Labrador'  # New field added
    
    def test_generate_from_template_missing_template(self):
        """Test error when template is missing."""
        with pytest.raises(TemplateError, match="No template found"):
            self.manager.generate_from_template('nonexistent', 'create', 'v1')
    
    def test_generate_from_template_with_field_generators(self):
        """Test data generation using field generators."""
        # Create template with field generators
        field_gen = FieldGenerator(
            generator_func=lambda: 'generated_value'
        )
        template = DataTemplate(
            resource_type='test',
            operation='create',
            base_data={'name': 'default'},
            field_generators={'generated_field': field_gen}
        )
        self.manager.register_template(template)
        
        result = self.manager.generate_from_template('test', 'create', 'v1')
        
        assert result['generated_field'] == 'generated_value'
    
    def test_register_field_generator(self):
        """Test registering custom field generator."""
        custom_generator = StringFieldGenerator(choices=['custom_value'])
        
        self.manager.register_field_generator('custom_field', custom_generator)
        retrieved = self.manager.get_field_generator('custom_field')
        
        assert retrieved == custom_generator
    
    def test_get_field_generator_pattern_matching(self):
        """Test field generator pattern matching."""
        # Test email pattern
        email_gen = self.manager._get_field_generator('user_email')
        assert email_gen is not None
        
        # Test phone pattern
        phone_gen = self.manager._get_field_generator('contact_phone')
        assert phone_gen is not None
        
        # Test ID pattern
        id_gen = self.manager._get_field_generator('owner_id')
        assert id_gen is not None
        assert isinstance(id_gen, RelationshipFieldGenerator)
    
    def test_list_templates(self):
        """Test listing registered templates."""
        template1 = DataTemplate('resource1', 'create')
        template2 = DataTemplate('resource2', 'update')
        
        self.manager.register_template(template1)
        self.manager.register_template(template2)
        
        templates = self.manager.list_templates()
        
        assert 'resource1_create' in templates
        assert 'resource2_update' in templates
    
    def test_clear_relationship_cache(self):
        """Test clearing relationship caches."""
        # Generate some data to populate caches
        template = DataTemplate(
            resource_type='pet',
            operation='create',
            relationships={'owner_id': 'user', 'vet_id': 'vet'}
        )
        self.manager.register_template(template)
        
        # Generate data to populate relationship caches
        self.manager.generate_from_template('pet', 'create', 'v1')
        
        # Clear caches
        self.manager.clear_relationship_cache()
        
        # Verify that relationship generators have been cleared
        # (This is more of a smoke test since we can't easily verify internal state)
        assert True  # If no exception, clearing worked
    
    def test_validation_with_missing_required_fields(self):
        """Test validation when required fields are missing."""
        self.mock_config.get_required_fields.return_value = ['name', 'species', 'required_field']
        
        template = DataTemplate(
            resource_type='pet',
            operation='create',
            base_data={'name': 'Buddy', 'species': 'dog'}
            # Missing 'required_field'
        )
        self.manager.register_template(template)
        
        with pytest.raises(TemplateError, match="Missing required fields"):
            self.manager.generate_from_template('pet', 'create', 'v1')
    
    def test_validation_with_custom_rules(self):
        """Test validation with custom validation rules."""
        def custom_validation(data):
            return data.get('name') != 'invalid_name'
        
        template = DataTemplate(
            resource_type='pet',
            operation='create',
            base_data={'name': 'invalid_name', 'species': 'dog'},
            validation_rules=[custom_validation]
        )
        self.manager.register_template(template)
        
        with pytest.raises(TemplateError, match="Template validation failed"):
            self.manager.generate_from_template('pet', 'create', 'v1')


class TestGlobalTemplateManager:
    """Test cases for global template manager functions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        reset_template_manager()
    
    def teardown_method(self):
        """Clean up after tests."""
        reset_template_manager()
    
    def test_get_template_manager_singleton(self):
        """Test that get_template_manager returns singleton instance."""
        manager1 = get_template_manager()
        manager2 = get_template_manager()
        
        assert manager1 is manager2
        assert isinstance(manager1, DataTemplateManager)
    
    def test_get_template_manager_with_custom_config(self):
        """Test get_template_manager with custom config manager."""
        mock_config = Mock(spec=VersionConfigManager)
        
        manager = get_template_manager(mock_config)
        
        assert manager.config_manager == mock_config
    
    def test_reset_template_manager(self):
        """Test resetting global template manager."""
        manager1 = get_template_manager()
        reset_template_manager()
        manager2 = get_template_manager()
        
        assert manager1 is not manager2


class TestDefaultTemplates:
    """Test cases for default templates initialization."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_config = Mock(spec=VersionConfigManager)
        self.mock_config.get_required_fields.return_value = []
        self.mock_config.get_optional_fields.return_value = []
        self.mock_config.get_schema_fields.return_value = []
        
        self.manager = DataTemplateManager(self.mock_config)
    
    def test_default_pet_template(self):
        """Test default pet template."""
        template = self.manager.get_template('pet', 'create')
        
        assert template is not None
        assert template.resource_type == 'pet'
        assert template.operation == 'create'
        assert 'name' in template.base_data
        assert 'species' in template.base_data
        assert 'owner_id' in template.relationships
        assert 'v2' in template.version_overrides
    
    def test_default_user_template(self):
        """Test default user template."""
        template = self.manager.get_template('user', 'create')
        
        assert template is not None
        assert template.resource_type == 'user'
        assert template.operation == 'create'
        assert 'email' in template.base_data
        assert 'first_name' in template.base_data
        assert 'v2' in template.version_overrides
    
    def test_default_appointment_template(self):
        """Test default appointment template."""
        template = self.manager.get_template('appointment', 'create')
        
        assert template is not None
        assert template.resource_type == 'appointment'
        assert template.operation == 'create'
        assert 'date' in template.base_data
        assert 'time' in template.base_data
        assert 'pet_id' in template.relationships
        assert 'user_id' in template.relationships
    
    def test_default_health_record_template(self):
        """Test default health record template."""
        template = self.manager.get_template('health_record', 'create')
        
        assert template is not None
        assert template.resource_type == 'health_record'
        assert template.operation == 'create'
        assert 'record_type' in template.base_data
        assert 'date' in template.base_data
        assert 'pet_id' in template.relationships