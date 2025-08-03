"""
Dynamic Test Data Factory for Version-Aware API Testing.

Generates version-appropriate test data based on configuration files,
handling version-specific fields, relationships, and validation requirements.
"""

import uuid
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union, Callable
from copy import deepcopy

from tests.dynamic.config_manager import get_config_manager, ConfigurationError
from tests.dynamic.templates import get_template_manager, DataTemplateManager, TemplateError


class TestDataGenerationError(Exception):
    """Raised when test data generation fails."""
    pass


class TestDataFactory:
    """Generates version-appropriate test data based on configuration."""
    
    def __init__(self, config_manager=None, template_manager=None):
        """
        Initialize the test data factory.
        
        Args:
            config_manager: Optional configuration manager instance
            template_manager: Optional template manager instance
        """
        self.config_manager = config_manager or get_config_manager()
        self.template_manager = template_manager or get_template_manager(self.config_manager)
        self._field_generators = self._initialize_field_generators()
        self._relationship_cache = {}
    
    def _initialize_field_generators(self) -> Dict[str, Callable]:
        """Initialize field generator functions for dynamic values."""
        return {
            'email': self._generate_email,
            'password': self._generate_password,
            'phone_number': self._generate_phone_number,
            'first_name': self._generate_first_name,
            'last_name': self._generate_last_name,
            'name': self._generate_pet_name,
            'species': self._generate_species,
            'breed': self._generate_breed,
            'gender': self._generate_gender,
            'weight': self._generate_weight,
            'color': self._generate_color,
            'temperament': self._generate_temperament,
            'behavioral_notes': self._generate_behavioral_notes,
            'emergency_contact': self._generate_emergency_contact,
            'address': self._generate_address,
            'date': self._generate_date,
            'time': self._generate_time,
            'reason': self._generate_appointment_reason,
            'notes': self._generate_notes,
            'veterinarian': self._generate_veterinarian,
            'record_type': self._generate_record_type,
            'description': self._generate_description,
            'cost': self._generate_cost,
            'owner_id': self._generate_owner_id,
            'pet_id': self._generate_pet_id,
            'user_id': self._generate_user_id,
        }
    
    def build_pet_data(self, version: str, use_template: bool = True, **overrides) -> Dict[str, Any]:
        """
        Generate pet data appropriate for the specified version.
        
        Args:
            version: API version (e.g., 'v1', 'v2')
            use_template: Whether to use template system for generation
            **overrides: Field values to override defaults
            
        Returns:
            Dictionary containing version-appropriate pet data
            
        Raises:
            TestDataGenerationError: If data generation fails
        """
        try:
            if use_template:
                return self.template_manager.generate_from_template('pet', 'create', version, **overrides)
            else:
                return self._build_resource_data(version, 'pet', 'create', **overrides)
        except (TemplateError, Exception) as e:
            # Fallback to direct generation if template fails
            try:
                return self._build_resource_data(version, 'pet', 'create', **overrides)
            except Exception as fallback_e:
                raise TestDataGenerationError(f"Failed to generate pet data for {version}: {e}, fallback: {fallback_e}")
    
    def build_user_data(self, version: str, use_template: bool = True, **overrides) -> Dict[str, Any]:
        """
        Generate user data appropriate for the specified version.
        
        Args:
            version: API version
            use_template: Whether to use template system for generation
            **overrides: Field values to override defaults
            
        Returns:
            Dictionary containing version-appropriate user data
        """
        try:
            if use_template:
                return self.template_manager.generate_from_template('user', 'create', version, **overrides)
            else:
                return self._build_resource_data(version, 'user', 'create', **overrides)
        except (TemplateError, Exception) as e:
            # Fallback to direct generation if template fails
            try:
                return self._build_resource_data(version, 'user', 'create', **overrides)
            except Exception as fallback_e:
                raise TestDataGenerationError(f"Failed to generate user data for {version}: {e}, fallback: {fallback_e}")
    
    def build_appointment_data(self, version: str, use_template: bool = True, **overrides) -> Dict[str, Any]:
        """
        Generate appointment data appropriate for the specified version.
        
        Args:
            version: API version
            use_template: Whether to use template system for generation
            **overrides: Field values to override defaults
            
        Returns:
            Dictionary containing version-appropriate appointment data
        """
        try:
            if use_template:
                return self.template_manager.generate_from_template('appointment', 'create', version, **overrides)
            else:
                return self._build_resource_data(version, 'appointment', 'create', **overrides)
        except (TemplateError, Exception) as e:
            # Fallback to direct generation if template fails
            try:
                return self._build_resource_data(version, 'appointment', 'create', **overrides)
            except Exception as fallback_e:
                raise TestDataGenerationError(f"Failed to generate appointment data for {version}: {e}, fallback: {fallback_e}")
    
    def build_health_record_data(self, version: str, use_template: bool = True, **overrides) -> Dict[str, Any]:
        """
        Generate health record data for versions that support it.
        
        Args:
            version: API version
            use_template: Whether to use template system for generation
            **overrides: Field values to override defaults
            
        Returns:
            Dictionary containing health record data
            
        Raises:
            TestDataGenerationError: If version doesn't support health records
        """
        if not self.config_manager.get_feature_availability(version, 'health_records'):
            raise TestDataGenerationError(f"Health records not supported in {version}")
        
        try:
            if use_template:
                return self.template_manager.generate_from_template('health_record', 'create', version, **overrides)
            else:
                return self._build_resource_data(version, 'health_record', 'create', **overrides)
        except (TemplateError, Exception) as e:
            # Fallback to direct generation if template fails
            try:
                return self._build_resource_data(version, 'health_record', 'create', **overrides)
            except Exception as fallback_e:
                raise TestDataGenerationError(f"Failed to generate health record data for {version}: {e}, fallback: {fallback_e}")
    
    def get_expected_response_fields(self, version: str, resource: str) -> List[str]:
        """
        Get expected response fields for a resource in the specified version.
        
        Args:
            version: API version
            resource: Resource type (pet, user, appointment, health_record)
            
        Returns:
            List of expected field names in response
        """
        schema_type = f"{resource}_response"
        try:
            return self.config_manager.get_schema_fields(version, schema_type)
        except ConfigurationError:
            return []
    
    def build_update_data(self, version: str, resource: str, **overrides) -> Dict[str, Any]:
        """
        Generate update data for a resource in the specified version.
        
        Args:
            version: API version
            resource: Resource type
            **overrides: Field values to override defaults
            
        Returns:
            Dictionary containing update data (subset of create fields)
        """
        try:
            # Generate full create data first
            full_data = self._build_resource_data(version, resource, 'create', **overrides)
            
            # For updates, typically exclude required fields that can't be changed
            # and include only a subset of fields
            update_data = {}
            
            # Get optional fields that can typically be updated
            optional_fields = self.config_manager.get_optional_fields(version, f"{resource}_create")
            
            # Include some optional fields in update
            for field in optional_fields:
                if field in full_data:
                    update_data[field] = full_data[field]
            
            # Apply any specific overrides
            update_data.update(overrides)
            
            return update_data
            
        except Exception as e:
            raise TestDataGenerationError(f"Failed to generate update data for {resource} in {version}: {e}")
    
    def _build_resource_data(self, version: str, resource: str, operation: str, **overrides) -> Dict[str, Any]:
        """
        Build resource data based on version configuration.
        
        Args:
            version: API version
            resource: Resource type
            operation: Operation type (create, update)
            **overrides: Field values to override
            
        Returns:
            Dictionary containing resource data
        """
        schema_type = f"{resource}_{operation}"
        
        # Start with default values from configuration
        try:
            data = self.config_manager.get_default_values(version, schema_type)
        except ConfigurationError:
            data = {}
        
        # Get required and optional fields for this version
        try:
            required_fields = self.config_manager.get_required_fields(version, schema_type)
            optional_fields = self.config_manager.get_optional_fields(version, schema_type)
            all_fields = required_fields + optional_fields
        except ConfigurationError:
            # Fallback to schema fields if required/optional not defined
            try:
                all_fields = self.config_manager.get_schema_fields(version, schema_type)
                required_fields = all_fields  # Assume all are required if not specified
                optional_fields = []
            except ConfigurationError:
                raise TestDataGenerationError(f"No schema configuration found for {schema_type} in {version}")
        
        # Generate values for fields that don't have defaults
        for field in all_fields:
            if field not in data:
                generated_value = self._generate_field_value(field, version, resource)
                if generated_value is not None:
                    data[field] = generated_value
        
        # Ensure all required fields are present
        for field in required_fields:
            if field not in data:
                generated_value = self._generate_field_value(field, version, resource)
                if generated_value is not None:
                    data[field] = generated_value
                else:
                    raise TestDataGenerationError(f"Could not generate required field '{field}' for {schema_type}")
        
        # Apply field mapping logic based on version configuration
        data = self._apply_version_field_mapping(data, version, resource, operation)
        
        # Apply any overrides
        data.update(overrides)
        
        # Validate generated data
        self._validate_generated_data(data, version, resource, operation)
        
        return data
    
    def _generate_field_value(self, field_name: str, version: str, resource: str) -> Any:
        """
        Generate a value for a specific field using appropriate generator.
        
        Args:
            field_name: Name of the field
            version: API version
            resource: Resource type
            
        Returns:
            Generated field value or None if no generator available
        """
        # Check if we have a specific generator for this field
        if field_name in self._field_generators:
            return self._field_generators[field_name]()
        
        # Handle relationship fields
        if field_name.endswith('_id'):
            return self._generate_relationship_id(field_name, version, resource)
        
        # Default generators based on field name patterns
        if 'email' in field_name.lower():
            return self._generate_email()
        elif 'phone' in field_name.lower():
            return self._generate_phone_number()
        elif 'name' in field_name.lower():
            return self._generate_name()
        elif 'date' in field_name.lower():
            return self._generate_date()
        elif 'time' in field_name.lower():
            return self._generate_time()
        elif 'cost' in field_name.lower() or 'price' in field_name.lower():
            return self._generate_cost()
        elif 'weight' in field_name.lower():
            return self._generate_weight()
        elif 'notes' in field_name.lower():
            return self._generate_notes()
        
        return None
    
    def _apply_version_field_mapping(self, data: Dict[str, Any], version: str, 
                                   resource: str, operation: str) -> Dict[str, Any]:
        """
        Apply version-specific field mapping logic.
        
        Args:
            data: Current data dictionary
            version: API version
            resource: Resource type
            operation: Operation type
            
        Returns:
            Data with version-specific field mappings applied
        """
        # Create a copy to avoid modifying original
        mapped_data = deepcopy(data)
        
        # Version-specific field transformations
        if version == 'v1':
            # Remove v2-specific fields if they exist
            v2_only_fields = ['temperament', 'behavioral_notes', 'emergency_contact', 
                            'address', 'owner_info', 'additional_photos', 'pet_count']
            for field in v2_only_fields:
                mapped_data.pop(field, None)
        
        elif version == 'v2':
            # Ensure v2-specific fields have appropriate structure
            if 'emergency_contact' in mapped_data and isinstance(mapped_data['emergency_contact'], dict):
                # Ensure emergency contact has required structure
                if 'name' not in mapped_data['emergency_contact']:
                    mapped_data['emergency_contact']['name'] = self._generate_first_name() + ' ' + self._generate_last_name()
                if 'phone' not in mapped_data['emergency_contact']:
                    mapped_data['emergency_contact']['phone'] = self._generate_phone_number()
            
            if 'address' in mapped_data and isinstance(mapped_data['address'], dict):
                # Ensure address has required structure
                required_address_fields = ['street', 'city', 'state', 'zip_code']
                for addr_field in required_address_fields:
                    if addr_field not in mapped_data['address']:
                        mapped_data['address'][addr_field] = self._generate_address_field(addr_field)
        
        return mapped_data
    
    def _validate_generated_data(self, data: Dict[str, Any], version: str, 
                               resource: str, operation: str) -> None:
        """
        Validate generated data against version schema requirements.
        
        Args:
            data: Generated data to validate
            version: API version
            resource: Resource type
            operation: Operation type
            
        Raises:
            TestDataGenerationError: If validation fails
        """
        schema_type = f"{resource}_{operation}"
        
        try:
            required_fields = self.config_manager.get_required_fields(version, schema_type)
        except ConfigurationError:
            # Skip validation if no requirements defined
            return
        
        # Check that all required fields are present
        missing_fields = []
        for field in required_fields:
            if field not in data or data[field] is None:
                missing_fields.append(field)
        
        if missing_fields:
            raise TestDataGenerationError(
                f"Missing required fields for {schema_type} in {version}: {missing_fields}"
            )
        
        # Validate field types and constraints
        self._validate_field_constraints(data, version, resource, operation)
    
    def _validate_field_constraints(self, data: Dict[str, Any], version: str, 
                                  resource: str, operation: str) -> None:
        """
        Validate field-specific constraints and types.
        
        Args:
            data: Data to validate
            version: API version
            resource: Resource type
            operation: Operation type
        """
        # Email validation
        if 'email' in data:
            email = data['email']
            if not isinstance(email, str) or '@' not in email:
                raise TestDataGenerationError(f"Invalid email format: {email}")
        
        # Weight validation
        if 'weight' in data:
            weight = data['weight']
            if not isinstance(weight, (int, float)) or weight <= 0:
                raise TestDataGenerationError(f"Invalid weight value: {weight}")
        
        # Date validation
        if 'date' in data:
            date_value = data['date']
            if isinstance(date_value, str):
                try:
                    datetime.fromisoformat(date_value.replace('Z', '+00:00'))
                except ValueError:
                    raise TestDataGenerationError(f"Invalid date format: {date_value}")
        
        # Cost validation
        if 'cost' in data:
            cost = data['cost']
            if not isinstance(cost, (int, float)) or cost < 0:
                raise TestDataGenerationError(f"Invalid cost value: {cost}")
    
    def _generate_relationship_id(self, field_name: str, version: str, resource: str) -> str:
        """
        Generate ID for relationship fields.
        
        Args:
            field_name: Name of the ID field
            version: API version
            resource: Resource type
            
        Returns:
            Generated UUID string
        """
        # Use cached IDs for consistency within test session
        cache_key = f"{version}_{resource}_{field_name}"
        if cache_key not in self._relationship_cache:
            self._relationship_cache[cache_key] = str(uuid.uuid4())
        
        return self._relationship_cache[cache_key]
    
    # Field generator methods
    def _generate_email(self) -> str:
        """Generate a random email address."""
        domains = ['example.com', 'test.org', 'demo.net']
        username = f"user{random.randint(1000, 9999)}"
        domain = random.choice(domains)
        return f"{username}@{domain}"
    
    def _generate_password(self) -> str:
        """Generate a test password."""
        return "TestPassword123!"
    
    def _generate_phone_number(self) -> str:
        """Generate a random phone number."""
        return f"555-{random.randint(1000, 9999)}"
    
    def _generate_first_name(self) -> str:
        """Generate a random first name."""
        names = ['John', 'Jane', 'Mike', 'Sarah', 'David', 'Lisa', 'Chris', 'Amy']
        return random.choice(names)
    
    def _generate_last_name(self) -> str:
        """Generate a random last name."""
        names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis']
        return random.choice(names)
    
    def _generate_name(self) -> str:
        """Generate a generic name."""
        return f"{self._generate_first_name()} {self._generate_last_name()}"
    
    def _generate_pet_name(self) -> str:
        """Generate a random pet name."""
        names = ['Buddy', 'Max', 'Bella', 'Charlie', 'Lucy', 'Cooper', 'Luna', 'Rocky']
        return random.choice(names)
    
    def _generate_species(self) -> str:
        """Generate a random species."""
        species = ['dog', 'cat', 'bird', 'rabbit', 'hamster']
        return random.choice(species)
    
    def _generate_breed(self) -> str:
        """Generate a random breed."""
        breeds = ['Golden Retriever', 'Labrador', 'Persian', 'Siamese', 'Parakeet', 'Holland Lop']
        return random.choice(breeds)
    
    def _generate_gender(self) -> str:
        """Generate a random gender."""
        genders = ['MALE', 'FEMALE']
        return random.choice(genders)
    
    def _generate_weight(self) -> float:
        """Generate a random weight."""
        return round(random.uniform(5.0, 100.0), 1)
    
    def _generate_color(self) -> str:
        """Generate a random color."""
        colors = ['Brown', 'Black', 'White', 'Golden', 'Gray', 'Orange', 'Spotted']
        return random.choice(colors)
    
    def _generate_temperament(self) -> str:
        """Generate a random temperament."""
        temperaments = ['Friendly', 'Calm', 'Energetic', 'Shy', 'Playful', 'Gentle']
        return random.choice(temperaments)
    
    def _generate_behavioral_notes(self) -> str:
        """Generate random behavioral notes."""
        notes = [
            'Good with children',
            'Needs regular exercise',
            'Friendly with other pets',
            'Requires gentle handling',
            'Very social and outgoing'
        ]
        return random.choice(notes)
    
    def _generate_emergency_contact(self) -> Dict[str, str]:
        """Generate emergency contact information."""
        return {
            'name': f"{self._generate_first_name()} {self._generate_last_name()}",
            'phone': self._generate_phone_number(),
            'relationship': random.choice(['Spouse', 'Parent', 'Sibling', 'Friend'])
        }
    
    def _generate_address(self) -> Dict[str, str]:
        """Generate address information."""
        return {
            'street': f"{random.randint(100, 9999)} {random.choice(['Main', 'Oak', 'Pine', 'Elm'])} St",
            'city': random.choice(['Springfield', 'Franklin', 'Georgetown', 'Madison']),
            'state': random.choice(['CA', 'NY', 'TX', 'FL', 'IL']),
            'zip_code': f"{random.randint(10000, 99999)}"
        }
    
    def _generate_address_field(self, field: str) -> str:
        """Generate a specific address field."""
        address = self._generate_address()
        return address.get(field, '')
    
    def _generate_date(self) -> str:
        """Generate a random date."""
        base_date = datetime.now()
        random_days = random.randint(-30, 30)
        date = base_date + timedelta(days=random_days)
        return date.strftime('%Y-%m-%d')
    
    def _generate_time(self) -> str:
        """Generate a random time."""
        hour = random.randint(8, 17)  # Business hours
        minute = random.choice([0, 15, 30, 45])
        return f"{hour:02d}:{minute:02d}"
    
    def _generate_appointment_reason(self) -> str:
        """Generate a random appointment reason."""
        reasons = [
            'Regular checkup',
            'Vaccination',
            'Dental cleaning',
            'Skin condition',
            'Follow-up visit',
            'Emergency visit'
        ]
        return random.choice(reasons)
    
    def _generate_notes(self) -> str:
        """Generate random notes."""
        notes = [
            'Standard appointment',
            'Patient is doing well',
            'Follow up in 2 weeks',
            'No issues reported',
            'Routine maintenance'
        ]
        return random.choice(notes)
    
    def _generate_veterinarian(self) -> str:
        """Generate a random veterinarian name."""
        titles = ['Dr.']
        first_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Davis']
        return f"{random.choice(titles)} {random.choice(first_names)}"
    
    def _generate_record_type(self) -> str:
        """Generate a random health record type."""
        types = ['VACCINATION', 'CHECKUP', 'SURGERY', 'MEDICATION', 'INJURY', 'ILLNESS']
        return random.choice(types)
    
    def _generate_description(self) -> str:
        """Generate a random description."""
        descriptions = [
            'Annual vaccination administered',
            'Routine health examination',
            'Minor surgical procedure',
            'Medication prescribed',
            'Treatment for minor injury',
            'Recovery from illness'
        ]
        return random.choice(descriptions)
    
    def _generate_cost(self) -> float:
        """Generate a random cost."""
        return round(random.uniform(25.0, 500.0), 2)
    
    def _generate_owner_id(self) -> str:
        """Generate owner ID."""
        return self._generate_relationship_id('owner_id', 'v1', 'pet')
    
    def _generate_pet_id(self) -> str:
        """Generate pet ID."""
        return self._generate_relationship_id('pet_id', 'v1', 'appointment')
    
    def _generate_user_id(self) -> str:
        """Generate user ID."""
        return self._generate_relationship_id('user_id', 'v1', 'appointment')
    
    def clear_relationship_cache(self) -> None:
        """Clear the relationship ID cache."""
        self._relationship_cache.clear()
        # Also clear template manager's relationship cache
        self.template_manager.clear_relationship_cache()
    
    def set_relationship_id(self, field_name: str, version: str, resource: str, value: str) -> None:
        """
        Set a specific relationship ID for consistency across tests.
        
        Args:
            field_name: Name of the ID field
            version: API version
            resource: Resource type
            value: ID value to use
        """
        cache_key = f"{version}_{resource}_{field_name}"
        self._relationship_cache[cache_key] = value
        
        # Also set in template manager if it has the field generator
        field_generator = self.template_manager.get_field_generator(field_name)
        if hasattr(field_generator, 'set_id'):
            field_generator.set_id(value)
    
    def validate_data_against_schema(self, data: Dict[str, Any], version: str, 
                                   resource: str, operation: str = 'create') -> List[str]:
        """
        Validate generated data against version schema and return any validation errors.
        
        Args:
            data: Data to validate
            version: API version
            resource: Resource type
            operation: Operation type
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        schema_type = f"{resource}_{operation}"
        
        try:
            # Check required fields
            required_fields = self.config_manager.get_required_fields(version, schema_type)
            for field in required_fields:
                if field not in data or data[field] is None:
                    errors.append(f"Missing required field: {field}")
            
            # Check field constraints
            field_errors = self._validate_field_constraints_list(data, version, resource, operation)
            errors.extend(field_errors)
            
        except ConfigurationError as e:
            errors.append(f"Configuration error during validation: {e}")
        
        return errors
    
    def _validate_field_constraints_list(self, data: Dict[str, Any], version: str, 
                                       resource: str, operation: str) -> List[str]:
        """
        Validate field constraints and return list of errors.
        
        Args:
            data: Data to validate
            version: API version
            resource: Resource type
            operation: Operation type
            
        Returns:
            List of validation error messages
        """
        errors = []
        
        # Email validation
        if 'email' in data:
            email = data['email']
            if not isinstance(email, str) or '@' not in email:
                errors.append(f"Invalid email format: {email}")
        
        # Weight validation
        if 'weight' in data:
            weight = data['weight']
            if not isinstance(weight, (int, float)) or weight <= 0:
                errors.append(f"Invalid weight value: {weight}")
        
        # Date validation
        if 'date' in data:
            date_value = data['date']
            if isinstance(date_value, str):
                try:
                    datetime.fromisoformat(date_value.replace('Z', '+00:00'))
                except ValueError:
                    errors.append(f"Invalid date format: {date_value}")
        
        # Cost validation
        if 'cost' in data:
            cost = data['cost']
            if not isinstance(cost, (int, float)) or cost < 0:
                errors.append(f"Invalid cost value: {cost}")
        
        # Version-specific validations
        if version == 'v2':
            # Validate complex fields structure
            if 'emergency_contact' in data and isinstance(data['emergency_contact'], dict):
                contact = data['emergency_contact']
                if 'name' not in contact or not contact['name']:
                    errors.append("Emergency contact missing name")
                if 'phone' not in contact or not contact['phone']:
                    errors.append("Emergency contact missing phone")
            
            if 'address' in data and isinstance(data['address'], dict):
                address = data['address']
                required_addr_fields = ['street', 'city', 'state', 'zip_code']
                for addr_field in required_addr_fields:
                    if addr_field not in address or not address[addr_field]:
                        errors.append(f"Address missing {addr_field}")
        
        return errors
    
    def build_related_data(self, version: str, relationships: Dict[str, str], 
                          **overrides) -> Dict[str, Dict[str, Any]]:
        """
        Build related data for multiple resources with consistent relationships.
        
        Args:
            version: API version
            relationships: Dictionary mapping resource types to their relationships
                          e.g., {'user': 'owner', 'pet': 'owned_pet', 'appointment': 'booking'}
            **overrides: Field overrides for specific resources
            
        Returns:
            Dictionary mapping resource types to their generated data
            
        Example:
            factory.build_related_data('v2', {
                'user': 'owner',
                'pet': 'owned_pet', 
                'appointment': 'booking'
            }, user_email='specific@email.com')
        """
        related_data = {}
        
        # Generate data for each resource type
        for resource_type, relationship_name in relationships.items():
            resource_overrides = {}
            
            # Extract resource-specific overrides
            prefix = f"{resource_type}_"
            for key, value in overrides.items():
                if key.startswith(prefix):
                    field_name = key[len(prefix):]
                    resource_overrides[field_name] = value
            
            # Generate data based on resource type
            if resource_type == 'user':
                related_data[resource_type] = self.build_user_data(version, **resource_overrides)
            elif resource_type == 'pet':
                # Set owner_id to match user if user was generated
                if 'user' in related_data:
                    resource_overrides.setdefault('owner_id', related_data['user'].get('id', str(uuid.uuid4())))
                related_data[resource_type] = self.build_pet_data(version, **resource_overrides)
            elif resource_type == 'appointment':
                # Set pet_id and user_id to match generated resources
                if 'pet' in related_data:
                    resource_overrides.setdefault('pet_id', related_data['pet'].get('id', str(uuid.uuid4())))
                if 'user' in related_data:
                    resource_overrides.setdefault('user_id', related_data['user'].get('id', str(uuid.uuid4())))
                related_data[resource_type] = self.build_appointment_data(version, **resource_overrides)
            elif resource_type == 'health_record':
                # Set pet_id to match pet if pet was generated
                if 'pet' in related_data:
                    resource_overrides.setdefault('pet_id', related_data['pet'].get('id', str(uuid.uuid4())))
                related_data[resource_type] = self.build_health_record_data(version, **resource_overrides)
        
        return related_data


# Global instance for easy access
_data_factory: Optional[TestDataFactory] = None


def get_data_factory(config_manager=None, template_manager=None) -> TestDataFactory:
    """
    Get the global test data factory instance.
    
    Args:
        config_manager: Optional configuration manager instance
        template_manager: Optional template manager instance
        
    Returns:
        TestDataFactory instance
    """
    global _data_factory
    
    if _data_factory is None:
        _data_factory = TestDataFactory(config_manager, template_manager)
    
    return _data_factory


def reset_data_factory() -> None:
    """Reset the global data factory (useful for testing)."""
    global _data_factory
    _data_factory = None