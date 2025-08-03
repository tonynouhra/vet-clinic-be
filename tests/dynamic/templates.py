"""
Data Template System for Dynamic API Testing Framework.

Provides base data templates, field generators, and relationship handling
for creating consistent and valid test data across API versions.
"""

import uuid
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union, Callable, Type
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from copy import deepcopy

from tests.dynamic.config_manager import get_config_manager, ConfigurationError


class TemplateError(Exception):
    """Raised when template operations fail."""
    pass


@dataclass
class FieldGenerator:
    """Configuration for a field generator function."""
    generator_func: Callable[[], Any]
    dependencies: List[str] = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)
    version_specific: bool = False


@dataclass
class DataTemplate:
    """Template for generating test data."""
    resource_type: str
    operation: str
    base_data: Dict[str, Any] = field(default_factory=dict)
    field_generators: Dict[str, FieldGenerator] = field(default_factory=dict)
    relationships: Dict[str, str] = field(default_factory=dict)
    version_overrides: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    validation_rules: List[Callable[[Dict[str, Any]], bool]] = field(default_factory=list)


class BaseFieldGenerator(ABC):
    """Abstract base class for field generators."""
    
    @abstractmethod
    def generate(self, context: Dict[str, Any] = None) -> Any:
        """Generate a field value."""
        pass
    
    def validate(self, value: Any, context: Dict[str, Any] = None) -> bool:
        """Validate a generated value."""
        return True


class StringFieldGenerator(BaseFieldGenerator):
    """Generator for string fields with various patterns."""
    
    def __init__(self, pattern: str = None, choices: List[str] = None, 
                 min_length: int = 1, max_length: int = 50):
        self.pattern = pattern
        self.choices = choices or []
        self.min_length = min_length
        self.max_length = max_length
    
    def generate(self, context: Dict[str, Any] = None) -> str:
        if self.choices:
            return random.choice(self.choices)
        
        if self.pattern:
            return self._generate_from_pattern(self.pattern)
        
        # Generate random string
        length = random.randint(self.min_length, min(self.max_length, 20))
        return ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=length))
    
    def _generate_from_pattern(self, pattern: str) -> str:
        """Generate string from pattern (simplified implementation)."""
        if pattern == 'email':
            return f"user{random.randint(1000, 9999)}@example.com"
        elif pattern == 'phone':
            return f"555-{random.randint(1000, 9999)}"
        elif pattern == 'name':
            names = ['John', 'Jane', 'Mike', 'Sarah', 'David', 'Lisa']
            return random.choice(names)
        else:
            return pattern


class NumericFieldGenerator(BaseFieldGenerator):
    """Generator for numeric fields."""
    
    def __init__(self, min_value: Union[int, float] = 0, 
                 max_value: Union[int, float] = 100, 
                 decimal_places: int = 0):
        self.min_value = min_value
        self.max_value = max_value
        self.decimal_places = decimal_places
    
    def generate(self, context: Dict[str, Any] = None) -> Union[int, float]:
        if self.decimal_places == 0:
            return random.randint(int(self.min_value), int(self.max_value))
        else:
            value = random.uniform(self.min_value, self.max_value)
            return round(value, self.decimal_places)


class DateTimeFieldGenerator(BaseFieldGenerator):
    """Generator for date and time fields."""
    
    def __init__(self, format_type: str = 'date', 
                 days_offset_range: tuple = (-30, 30)):
        self.format_type = format_type
        self.days_offset_range = days_offset_range
    
    def generate(self, context: Dict[str, Any] = None) -> str:
        base_date = datetime.now()
        offset_days = random.randint(*self.days_offset_range)
        target_date = base_date + timedelta(days=offset_days)
        
        if self.format_type == 'date':
            return target_date.strftime('%Y-%m-%d')
        elif self.format_type == 'time':
            # Generate business hours time
            hour = random.randint(8, 17)
            minute = random.choice([0, 15, 30, 45])
            return f"{hour:02d}:{minute:02d}"
        elif self.format_type == 'datetime':
            return target_date.isoformat()
        else:
            return target_date.strftime('%Y-%m-%d')


class RelationshipFieldGenerator(BaseFieldGenerator):
    """Generator for relationship ID fields."""
    
    def __init__(self, related_resource: str, cache_key: str = None):
        self.related_resource = related_resource
        self.cache_key = cache_key
        self._id_cache = {}
    
    def generate(self, context: Dict[str, Any] = None) -> str:
        cache_key = self.cache_key or f"{self.related_resource}_id"
        
        if cache_key not in self._id_cache:
            self._id_cache[cache_key] = str(uuid.uuid4())
        
        return self._id_cache[cache_key]
    
    def set_id(self, id_value: str, cache_key: str = None) -> None:
        """Set a specific ID value for consistency."""
        key = cache_key or f"{self.related_resource}_id"
        self._id_cache[key] = id_value
    
    def clear_cache(self) -> None:
        """Clear the ID cache."""
        self._id_cache.clear()


class ComplexFieldGenerator(BaseFieldGenerator):
    """Generator for complex nested objects."""
    
    def __init__(self, template: Dict[str, Any], 
                 field_generators: Dict[str, BaseFieldGenerator] = None):
        self.template = template
        self.field_generators = field_generators or {}
    
    def generate(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        result = deepcopy(self.template)
        
        for field_name, generator in self.field_generators.items():
            if field_name in result:
                result[field_name] = generator.generate(context)
        
        return result


class DataTemplateManager:
    """Manages data templates and provides template-based data generation."""
    
    def __init__(self, config_manager=None):
        self.config_manager = config_manager or get_config_manager()
        self._templates: Dict[str, DataTemplate] = {}
        self._field_generators: Dict[str, BaseFieldGenerator] = {}
        self._initialize_default_generators()
        self._initialize_default_templates()
    
    def _initialize_default_generators(self) -> None:
        """Initialize default field generators."""
        self._field_generators.update({
            'email': StringFieldGenerator(pattern='email'),
            'password': StringFieldGenerator(choices=['TestPassword123!']),
            'phone_number': StringFieldGenerator(pattern='phone'),
            'first_name': StringFieldGenerator(choices=[
                'John', 'Jane', 'Mike', 'Sarah', 'David', 'Lisa', 'Chris', 'Amy'
            ]),
            'last_name': StringFieldGenerator(choices=[
                'Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia'
            ]),
            'pet_name': StringFieldGenerator(choices=[
                'Buddy', 'Max', 'Bella', 'Charlie', 'Lucy', 'Cooper', 'Luna'
            ]),
            'species': StringFieldGenerator(choices=[
                'dog', 'cat', 'bird', 'rabbit', 'hamster'
            ]),
            'breed': StringFieldGenerator(choices=[
                'Golden Retriever', 'Labrador', 'Persian', 'Siamese', 'Parakeet'
            ]),
            'gender': StringFieldGenerator(choices=['MALE', 'FEMALE']),
            'color': StringFieldGenerator(choices=[
                'Brown', 'Black', 'White', 'Golden', 'Gray', 'Orange'
            ]),
            'temperament': StringFieldGenerator(choices=[
                'Friendly', 'Calm', 'Energetic', 'Shy', 'Playful', 'Gentle'
            ]),
            'weight': NumericFieldGenerator(min_value=1.0, max_value=100.0, decimal_places=1),
            'cost': NumericFieldGenerator(min_value=25.0, max_value=500.0, decimal_places=2),
            'date': DateTimeFieldGenerator(format_type='date'),
            'time': DateTimeFieldGenerator(format_type='time'),
            'owner_id': RelationshipFieldGenerator('user', 'owner_id'),
            'pet_id': RelationshipFieldGenerator('pet', 'pet_id'),
            'user_id': RelationshipFieldGenerator('user', 'user_id'),
            'emergency_contact': ComplexFieldGenerator(
                template={'name': '', 'phone': '', 'relationship': ''},
                field_generators={
                    'name': StringFieldGenerator(pattern='name'),
                    'phone': StringFieldGenerator(pattern='phone'),
                    'relationship': StringFieldGenerator(choices=[
                        'Spouse', 'Parent', 'Sibling', 'Friend'
                    ])
                }
            ),
            'address': ComplexFieldGenerator(
                template={'street': '', 'city': '', 'state': '', 'zip_code': ''},
                field_generators={
                    'street': StringFieldGenerator(choices=[
                        '123 Main St', '456 Oak Ave', '789 Pine Rd'
                    ]),
                    'city': StringFieldGenerator(choices=[
                        'Springfield', 'Franklin', 'Georgetown', 'Madison'
                    ]),
                    'state': StringFieldGenerator(choices=['CA', 'NY', 'TX', 'FL']),
                    'zip_code': StringFieldGenerator(choices=[
                        '12345', '67890', '54321', '98765'
                    ])
                }
            )
        })
    
    def _initialize_default_templates(self) -> None:
        """Initialize default data templates for common resources."""
        # Pet templates
        self.register_template(DataTemplate(
            resource_type='pet',
            operation='create',
            base_data={
                'name': 'Buddy',
                'species': 'dog',
                'breed': 'Golden Retriever',
                'gender': 'MALE',
                'weight': 65.5,
                'color': 'Golden'
            },
            relationships={'owner_id': 'user'},
            version_overrides={
                'v2': {
                    'temperament': 'Friendly',
                    'behavioral_notes': 'Good with children',
                    'emergency_contact': {
                        'name': 'John Doe',
                        'phone': '555-0123',
                        'relationship': 'Owner'
                    }
                }
            }
        ))
        
        # User templates
        self.register_template(DataTemplate(
            resource_type='user',
            operation='create',
            base_data={
                'email': 'user@example.com',
                'password': 'TestPassword123!',
                'first_name': 'John',
                'last_name': 'Doe',
                'phone_number': '555-0123',
                'role': 'PET_OWNER'
            },
            version_overrides={
                'v2': {
                    'address': {
                        'street': '123 Main St',
                        'city': 'Anytown',
                        'state': 'CA',
                        'zip_code': '12345'
                    },
                    'emergency_contact': {
                        'name': 'Jane Doe',
                        'phone': '555-0456',
                        'relationship': 'Spouse'
                    }
                }
            }
        ))
        
        # Appointment templates
        self.register_template(DataTemplate(
            resource_type='appointment',
            operation='create',
            base_data={
                'date': '2024-01-15',
                'time': '10:00',
                'reason': 'Regular checkup'
            },
            relationships={
                'pet_id': 'pet',
                'user_id': 'user'
            },
            version_overrides={
                'v2': {
                    'notes': 'Standard appointment',
                    'veterinarian': 'Dr. Smith'
                }
            }
        ))
        
        # Health record templates (v2 only)
        self.register_template(DataTemplate(
            resource_type='health_record',
            operation='create',
            base_data={
                'record_type': 'VACCINATION',
                'date': '2024-01-15',
                'description': 'Annual vaccination',
                'veterinarian': 'Dr. Smith',
                'cost': 75.00,
                'notes': 'No adverse reactions'
            },
            relationships={'pet_id': 'pet'}
        ))
    
    def register_template(self, template: DataTemplate) -> None:
        """
        Register a data template.
        
        Args:
            template: DataTemplate instance to register
        """
        key = f"{template.resource_type}_{template.operation}"
        self._templates[key] = template
    
    def get_template(self, resource_type: str, operation: str) -> Optional[DataTemplate]:
        """
        Get a registered template.
        
        Args:
            resource_type: Type of resource (pet, user, etc.)
            operation: Operation type (create, update)
            
        Returns:
            DataTemplate instance or None if not found
        """
        key = f"{resource_type}_{operation}"
        return self._templates.get(key)
    
    def generate_from_template(self, resource_type: str, operation: str, 
                             version: str, **overrides) -> Dict[str, Any]:
        """
        Generate data using a template.
        
        Args:
            resource_type: Type of resource
            operation: Operation type
            version: API version
            **overrides: Field values to override
            
        Returns:
            Generated data dictionary
            
        Raises:
            TemplateError: If template not found or generation fails
        """
        template = self.get_template(resource_type, operation)
        if not template:
            raise TemplateError(f"No template found for {resource_type}_{operation}")
        
        try:
            return self._generate_data_from_template(template, version, **overrides)
        except Exception as e:
            raise TemplateError(f"Failed to generate data from template: {e}")
    
    def _generate_data_from_template(self, template: DataTemplate, version: str, 
                                   **overrides) -> Dict[str, Any]:
        """
        Generate data from a specific template.
        
        Args:
            template: DataTemplate to use
            version: API version
            **overrides: Field overrides
            
        Returns:
            Generated data dictionary
        """
        # Start with base data
        data = deepcopy(template.base_data)
        
        # Apply version-specific overrides
        if version in template.version_overrides:
            version_data = deepcopy(template.version_overrides[version])
            data.update(version_data)
        
        # Generate relationship IDs
        for field_name, related_resource in template.relationships.items():
            if field_name not in data:
                generator = self._field_generators.get(field_name)
                if generator:
                    data[field_name] = generator.generate()
                else:
                    data[field_name] = str(uuid.uuid4())
        
        # Generate missing fields using field generators
        schema_type = f"{template.resource_type}_{template.operation}"
        try:
            required_fields = self.config_manager.get_required_fields(version, schema_type)
            optional_fields = self.config_manager.get_optional_fields(version, schema_type)
            all_fields = required_fields + optional_fields
        except ConfigurationError:
            # Fallback to schema fields
            try:
                all_fields = self.config_manager.get_schema_fields(version, schema_type)
            except ConfigurationError:
                all_fields = list(data.keys())
        
        # Generate values for missing fields
        for field_name in all_fields:
            if field_name not in data:
                generator = self._get_field_generator(field_name)
                if generator:
                    data[field_name] = generator.generate()
        
        # Apply field-specific generators from template
        for field_name, field_generator in template.field_generators.items():
            if field_name in all_fields or field_name not in data:
                data[field_name] = field_generator.generator_func()
        
        # Apply overrides
        data.update(overrides)
        
        # Validate generated data
        self._validate_template_data(data, template, version)
        
        return data
    
    def _get_field_generator(self, field_name: str) -> Optional[BaseFieldGenerator]:
        """
        Get appropriate field generator for a field name.
        
        Args:
            field_name: Name of the field
            
        Returns:
            BaseFieldGenerator instance or None
        """
        # Direct match
        if field_name in self._field_generators:
            return self._field_generators[field_name]
        
        # Pattern matching
        if 'email' in field_name.lower():
            return self._field_generators.get('email')
        elif 'phone' in field_name.lower():
            return self._field_generators.get('phone_number')
        elif field_name.endswith('_name') or field_name == 'name':
            if 'pet' in field_name.lower():
                return self._field_generators.get('pet_name')
            else:
                return self._field_generators.get('first_name')
        elif field_name.endswith('_id'):
            # Create relationship generator
            related_resource = field_name.replace('_id', '')
            return RelationshipFieldGenerator(related_resource, field_name)
        elif 'date' in field_name.lower():
            return self._field_generators.get('date')
        elif 'time' in field_name.lower():
            return self._field_generators.get('time')
        elif 'cost' in field_name.lower() or 'price' in field_name.lower():
            return self._field_generators.get('cost')
        elif 'weight' in field_name.lower():
            return self._field_generators.get('weight')
        
        return None
    
    def _validate_template_data(self, data: Dict[str, Any], template: DataTemplate, 
                              version: str) -> None:
        """
        Validate generated data against template rules.
        
        Args:
            data: Generated data
            template: Template used for generation
            version: API version
            
        Raises:
            TemplateError: If validation fails
        """
        # Run template-specific validation rules
        for validation_rule in template.validation_rules:
            if not validation_rule(data):
                raise TemplateError(f"Template validation failed for {template.resource_type}")
        
        # Validate required fields
        schema_type = f"{template.resource_type}_{template.operation}"
        try:
            required_fields = self.config_manager.get_required_fields(version, schema_type)
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                raise TemplateError(f"Missing required fields: {missing_fields}")
        except ConfigurationError:
            pass  # Skip validation if no configuration available
    
    def register_field_generator(self, field_name: str, generator: BaseFieldGenerator) -> None:
        """
        Register a custom field generator.
        
        Args:
            field_name: Name of the field
            generator: BaseFieldGenerator instance
        """
        self._field_generators[field_name] = generator
    
    def get_field_generator(self, field_name: str) -> Optional[BaseFieldGenerator]:
        """
        Get a field generator by name.
        
        Args:
            field_name: Name of the field
            
        Returns:
            BaseFieldGenerator instance or None
        """
        return self._field_generators.get(field_name)
    
    def list_templates(self) -> List[str]:
        """
        List all registered template keys.
        
        Returns:
            List of template keys
        """
        return list(self._templates.keys())
    
    def clear_relationship_cache(self) -> None:
        """Clear all relationship ID caches."""
        for generator in self._field_generators.values():
            if isinstance(generator, RelationshipFieldGenerator):
                generator.clear_cache()


# Global instance for easy access
_template_manager: Optional[DataTemplateManager] = None


def get_template_manager(config_manager=None) -> DataTemplateManager:
    """
    Get the global template manager instance.
    
    Args:
        config_manager: Optional configuration manager instance
        
    Returns:
        DataTemplateManager instance
    """
    global _template_manager
    
    if _template_manager is None:
        _template_manager = DataTemplateManager(config_manager)
    
    return _template_manager


def reset_template_manager() -> None:
    """Reset the global template manager (useful for testing)."""
    global _template_manager
    _template_manager = None