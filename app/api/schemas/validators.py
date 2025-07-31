"""
Schema validation utilities for version-agnostic validation.

This module provides utilities for validating schemas across different API versions,
handling version-specific validation rules, and managing schema evolution.
"""

from typing import Dict, Any, List, Optional, Type, Union, Callable
from pydantic import BaseModel, ValidationError
from .base import BaseSchema


class ValidationResult:
    """Result of schema validation with detailed information."""
    
    def __init__(self, is_valid: bool, data: Dict[str, Any] = None, errors: List[str] = None):
        self.is_valid = is_valid
        self.data = data or {}
        self.errors = errors or []
    
    def add_error(self, error: str):
        """Add an error to the validation result."""
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str):
        """Add a warning to the validation result."""
        if not hasattr(self, 'warnings'):
            self.warnings = []
        self.warnings.append(warning)


class VersionAwareValidator:
    """Validator that can handle multiple schema versions."""
    
    def __init__(self):
        self.version_schemas: Dict[str, Dict[str, Type[BaseModel]]] = {}
        self.validation_rules: Dict[str, List[Callable]] = {}
        self.migration_functions: Dict[str, Callable] = {}
    
    def register_schema(self, version: str, resource: str, schema: Type[BaseModel]):
        """Register a schema for a specific version and resource."""
        if version not in self.version_schemas:
            self.version_schemas[version] = {}
        self.version_schemas[version][resource] = schema
    
    def register_validation_rule(self, version: str, rule: Callable):
        """Register a custom validation rule for a version."""
        if version not in self.validation_rules:
            self.validation_rules[version] = []
        self.validation_rules[version].append(rule)
    
    def register_migration(self, from_version: str, to_version: str, migration_func: Callable):
        """Register a migration function between versions."""
        key = f"{from_version}_to_{to_version}"
        self.migration_functions[key] = migration_func
    
    def validate(
        self, 
        data: Dict[str, Any], 
        version: str, 
        resource: str,
        strict: bool = True
    ) -> ValidationResult:
        """
        Validate data against a specific version schema.
        
        Args:
            data: Data to validate
            version: API version
            resource: Resource type (users, pets, etc.)
            strict: Whether to use strict validation
        
        Returns:
            ValidationResult with validation outcome
        """
        schema = self.version_schemas.get(version, {}).get(resource)
        if not schema:
            return ValidationResult(
                is_valid=False, 
                errors=[f"No schema found for version {version}, resource {resource}"]
            )
        
        try:
            # Validate with Pydantic schema
            validated_data = schema(**data)
            result = ValidationResult(is_valid=True, data=validated_data.model_dump())
            
            # Apply custom validation rules
            version_rules = self.validation_rules.get(version, [])
            for rule in version_rules:
                try:
                    rule_result = rule(validated_data.model_dump())
                    if not rule_result.get('valid', True):
                        result.add_error(rule_result.get('error', 'Custom validation failed'))
                except Exception as e:
                    if strict:
                        result.add_error(f"Custom validation rule failed: {str(e)}")
                    else:
                        result.add_warning(f"Custom validation rule warning: {str(e)}")
            
            return result
            
        except ValidationError as e:
            errors = [f"{error['loc'][0] if error['loc'] else 'field'}: {error['msg']}" 
                     for error in e.errors()]
            return ValidationResult(is_valid=False, errors=errors)
        except Exception as e:
            return ValidationResult(is_valid=False, errors=[f"Validation failed: {str(e)}"])
    
    def validate_with_fallback(
        self, 
        data: Dict[str, Any], 
        primary_version: str, 
        fallback_version: str, 
        resource: str
    ) -> ValidationResult:
        """
        Validate with primary version, falling back to secondary version.
        
        Args:
            data: Data to validate
            primary_version: Primary version to try
            fallback_version: Fallback version if primary fails
            resource: Resource type
        
        Returns:
            ValidationResult with validation outcome
        """
        # Try primary version first
        result = self.validate(data, primary_version, resource, strict=False)
        if result.is_valid:
            return result
        
        # Try fallback version
        fallback_result = self.validate(data, fallback_version, resource, strict=False)
        if fallback_result.is_valid:
            # Try to migrate data to primary version
            migration_key = f"{fallback_version}_to_{primary_version}"
            migration_func = self.migration_functions.get(migration_key)
            
            if migration_func:
                try:
                    migrated_data = migration_func(fallback_result.data)
                    final_result = self.validate(migrated_data, primary_version, resource)
                    if final_result.is_valid:
                        final_result.add_warning(f"Data migrated from {fallback_version} to {primary_version}")
                        return final_result
                except Exception as e:
                    fallback_result.add_warning(f"Migration failed: {str(e)}")
            
            fallback_result.add_warning(f"Using {fallback_version} schema as fallback")
            return fallback_result
        
        # Both validations failed
        result.errors.extend([f"Fallback validation also failed: {err}" for err in fallback_result.errors])
        return result
    
    def get_schema_info(self, version: str, resource: str) -> Dict[str, Any]:
        """Get information about a schema."""
        schema = self.version_schemas.get(version, {}).get(resource)
        if not schema:
            return {}
        
        fields_info = {}
        for field_name, field_info in schema.model_fields.items():
            fields_info[field_name] = {
                'type': str(field_info.annotation),
                'required': field_info.is_required(),
                'default': getattr(field_info, 'default', None)
            }
        
        return {
            'schema_name': schema.__name__,
            'fields': fields_info,
            'field_count': len(fields_info)
        }


# Global validator instance
global_validator = VersionAwareValidator()


# Convenience functions
def validate_v1_data(data: Dict[str, Any], resource: str) -> ValidationResult:
    """Validate data against V1 schema."""
    return global_validator.validate(data, "v1", resource)


def validate_v2_data(data: Dict[str, Any], resource: str) -> ValidationResult:
    """Validate data against V2 schema."""
    return global_validator.validate(data, "v2", resource)


def validate_with_version_fallback(
    data: Dict[str, Any], 
    resource: str, 
    primary_version: str = "v2", 
    fallback_version: str = "v1"
) -> ValidationResult:
    """Validate data with version fallback."""
    return global_validator.validate_with_fallback(
        data, primary_version, fallback_version, resource
    )


# Schema comparison utilities
def compare_version_schemas(version1: str, version2: str, resource: str) -> Dict[str, Any]:
    """Compare schemas between two versions."""
    schema1 = global_validator.version_schemas.get(version1, {}).get(resource)
    schema2 = global_validator.version_schemas.get(version2, {}).get(resource)
    
    if not schema1 or not schema2:
        return {"error": "One or both schemas not found"}
    
    fields1 = set(schema1.model_fields.keys())
    fields2 = set(schema2.model_fields.keys())
    
    return {
        "common_fields": list(fields1 & fields2),
        "added_in_v2": list(fields2 - fields1),
        "removed_in_v2": list(fields1 - fields2),
        "compatibility_score": len(fields1 & fields2) / len(fields1 | fields2) if fields1 | fields2 else 0
    }


# Custom validation rules
def create_business_rule_validator(rule_name: str, validation_func: Callable) -> Callable:
    """Create a business rule validator."""
    def validator(data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            is_valid = validation_func(data)
            return {
                "valid": is_valid,
                "rule": rule_name,
                "error": f"Business rule '{rule_name}' validation failed" if not is_valid else None
            }
        except Exception as e:
            return {
                "valid": False,
                "rule": rule_name,
                "error": f"Business rule '{rule_name}' execution failed: {str(e)}"
            }
    
    return validator


# Schema evolution utilities
def create_field_migration_rule(old_field: str, new_field: str, transform_func: Callable = None):
    """Create a field migration rule."""
    def migration(data: Dict[str, Any]) -> Dict[str, Any]:
        migrated_data = data.copy()
        
        if old_field in migrated_data:
            old_value = migrated_data.pop(old_field)
            if transform_func:
                new_value = transform_func(old_value)
            else:
                new_value = old_value
            migrated_data[new_field] = new_value
        
        return migrated_data
    
    return migration


def create_default_value_migration(field: str, default_value: Any):
    """Create a migration that adds default values for new fields."""
    def migration(data: Dict[str, Any]) -> Dict[str, Any]:
        migrated_data = data.copy()
        if field not in migrated_data:
            migrated_data[field] = default_value
        return migrated_data
    
    return migration


# Field validation utilities
from pydantic import Field, EmailStr, validator
import re
from typing import Any


def validate_email(email: str) -> bool:
    """Validate email format."""
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(email_pattern, email))


def validate_phone(phone: str) -> bool:
    """Validate phone number format."""
    if not phone:
        return True  # Optional field
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', phone)
    # Check if it's a valid length (10-15 digits)
    return 10 <= len(digits_only) <= 15


def validate_positive_integer(value: int) -> bool:
    """Validate that a value is a positive integer."""
    return isinstance(value, int) and value > 0


# Field factory functions
def email_field(description: str, default: Any = ...) -> Field:
    """Create an email field with validation."""
    return Field(
        default=default,
        description=description,
        regex=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )


def phone_field(description: str, default: Any = None) -> Field:
    """Create a phone field with validation."""
    return Field(
        default=default,
        description=description,
        regex=r'^\+?[\d\s\-\(\)]{10,15}$'
    )


def non_empty_string_field(description: str, max_length: int = None) -> Field:
    """Create a non-empty string field."""
    return Field(
        description=description,
        min_length=1,
        max_length=max_length,
        strip_whitespace=True
    )


def positive_int_field(description: str, default: Any = ...) -> Field:
    """Create a positive integer field."""
    return Field(
        default=default,
        description=description,
        gt=0
    )


def positive_float_field(description: str, default: Any = ...) -> Field:
    """Create a positive float field."""
    return Field(
        default=default,
        description=description,
        gt=0.0
    )


# Schema validation mixin
class SchemaValidationMixin:
    """Mixin for additional schema validation methods."""
    
    @validator('*', pre=True)
    def strip_strings(cls, v):
        """Strip whitespace from string fields."""
        if isinstance(v, str):
            return v.strip()
        return v
    
    def validate_required_fields(self, required_fields: list) -> bool:
        """Validate that required fields are present and not empty."""
        for field in required_fields:
            value = getattr(self, field, None)
            if value is None or (isinstance(value, str) and not value.strip()):
                return False
        return True
    
    def get_changed_fields(self, original_data: dict) -> dict:
        """Get fields that have changed from original data."""
        current_data = self.dict()
        changed = {}
        
        for key, value in current_data.items():
            if key in original_data and original_data[key] != value:
                changed[key] = {
                    'old': original_data[key],
                    'new': value
                }
        
        return changed