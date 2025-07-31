"""
Schema validation utilities for version-agnostic validation.

This module provides utilities for validating schemas across different API versions,
handling version-specific validation rules, and managing schema evolution.
"""

from typing import Dict, Any, List, Optional, Type, Union, Callable
from pydantic import BaseModel, ValidationError


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
                except (TypeError, ValueError, KeyError) as e:
                    error_msg = f"Custom validation rule failed - {type(e).__name__}: {str(e)}"
                    if strict:
                        result.add_error(error_msg)
                    else:
                        result.add_warning(f"Custom validation rule warning - {type(e).__name__}: {str(e)}")
                except AttributeError as e:
                    error_msg = f"Custom validation rule configuration error - {type(e).__name__}: {str(e)}"
                    if strict:
                        result.add_error(error_msg)
                    else:
                        result.add_warning(error_msg)
                except Exception as e:
                    error_msg = f"Unexpected error in custom validation rule - {type(e).__name__}: {str(e)}"
                    if strict:
                        result.add_error(error_msg)
                    else:
                        result.add_warning(error_msg)

            return result

        except ValidationError as e:
            errors = [f"{error['loc'][0] if error['loc'] else 'field'}: {error['msg']}"
                     for error in e.errors()]
            return ValidationResult(is_valid=False, errors=errors)
        except TypeError as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Schema instantiation failed - invalid data types: {str(e)}"]
            )
        except ValueError as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Schema validation failed - invalid values: {str(e)}"]
            )
        except KeyError as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Schema validation failed - missing required field: {str(e)}"]
            )
        except AttributeError as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Schema configuration error - invalid schema structure: {str(e)}"]
            )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Unexpected validation error - {type(e).__name__}: {str(e)}"]
            )
    
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


# Dynamic validation functions - scalable for any number of versions
def validate_data_by_version(data: Dict[str, Any], version: str, resource: str) -> ValidationResult:
    """Generic validation function that works with any version."""
    return global_validator.validate(data, version, resource)


def validate_data_with_latest(
    data: Dict[str, Any], 
    resource: str,
    fallback_versions: List[str] = None
) -> ValidationResult:
    """Validate using the latest version with fallback to older versions."""
    if fallback_versions is None:
        # Get from your SUPPORTED_VERSIONS config
        from . import SUPPORTED_VERSIONS
        fallback_versions = sorted(SUPPORTED_VERSIONS, reverse=True)
    
    primary_version = fallback_versions[0] if fallback_versions else "v2"
    
    for version in fallback_versions:
        result = global_validator.validate(data, version, resource, strict=False)
        if result.is_valid:
            if version != primary_version:
                result.add_warning(f"Validated with {version} instead of {primary_version}")
            return result
    
    # If all versions fail, return the result from the primary version
    return global_validator.validate(data, primary_version, resource)


# Generic validation with smart fallback
def validate_with_smart_fallback(
    data: Dict[str, Any], 
    resource: str,
    preferred_version: str = None
) -> ValidationResult:
    """Smart validation that tries preferred version first, then falls back."""
    from . import DEFAULT_VERSION, SUPPORTED_VERSIONS
    
    if preferred_version is None:
        preferred_version = DEFAULT_VERSION
    
    # Try preferred version first
    result = validate_data_by_version(data, preferred_version, resource)
    if result.is_valid:
        return result
    
    # Try other versions as fallback
    other_versions = [v for v in SUPPORTED_VERSIONS if v != preferred_version]
    for version in reversed(other_versions):  # Try newer versions first
        result = validate_data_by_version(data, version, resource)
        if result.is_valid:
            result.add_warning(f"Validated with {version} fallback instead of {preferred_version}")
            return result
    
    # Return original failure if nothing works
    return validate_data_by_version(data, preferred_version, resource)


# Keep convenience functions but make them dynamic (legacy support)
def validate_v1_data(data: Dict[str, Any], resource: str) -> ValidationResult:
    """Validate data against V1 schema (legacy support)."""
    return validate_data_by_version(data, "v1", resource)


def validate_v2_data(data: Dict[str, Any], resource: str) -> ValidationResult:
    """Validate data against V2 schema (legacy support)."""
    return validate_data_by_version(data, "v2", resource)


def validate_with_version_fallback(
    data: Dict[str, Any], 
    resource: str, 
    primary_version: str = "v2", 
    fallback_version: str = "v1"
) -> ValidationResult:
    """Validate data with version fallback (legacy support)."""
    return global_validator.validate_with_fallback(
        data, primary_version, fallback_version, resource
    )


# Version management utilities
def get_supported_versions() -> List[str]:
    """Get list of all supported API versions."""
    from . import SUPPORTED_VERSIONS
    return SUPPORTED_VERSIONS


def get_latest_version() -> str:
    """Get the latest supported API version."""
    from . import DEFAULT_VERSION
    return DEFAULT_VERSION


def is_version_supported(version: str) -> bool:
    """Check if a version is supported."""
    return version in get_supported_versions()


def get_version_for_resource(resource: str, preferred_version: str = None) -> str:
    """Get the best version to use for a specific resource."""
    if preferred_version and is_version_supported(preferred_version):
        # Check if the resource exists in the preferred version
        if global_validator.version_schemas.get(preferred_version, {}).get(resource):
            return preferred_version
    
    # Fall back to latest version that has this resource
    for version in reversed(get_supported_versions()):
        if global_validator.version_schemas.get(version, {}).get(resource):
            return version
    
    # Default to latest version
    return get_latest_version()


def validate_with_auto_version(data: Dict[str, Any], resource: str) -> ValidationResult:
    """Automatically select the best version for validation."""
    best_version = get_version_for_resource(resource)
    return validate_data_by_version(data, best_version, resource)


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
        except TypeError as e:
            return {
                "valid": False,
                "rule": rule_name,
                "error": f"Business rule '{rule_name}' type error - invalid data types: {str(e)}"
            }
        except ValueError as e:
            return {
                "valid": False,
                "rule": rule_name,
                "error": f"Business rule '{rule_name}' value error - invalid values: {str(e)}"
            }
        except KeyError as e:
            return {
                "valid": False,
                "rule": rule_name,
                "error": f"Business rule '{rule_name}' key error - missing field: {str(e)}"
            }
        except AttributeError as e:
            return {
                "valid": False,
                "rule": rule_name,
                "error": f"Business rule '{rule_name}' attribute error - invalid attribute access: {str(e)}"
            }
        except Exception as e:
            return {
                "valid": False,
                "rule": rule_name,
                "error": f"Business rule '{rule_name}' unexpected error - {type(e).__name__}: {str(e)}"
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
        pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )


def phone_field(description: str, default: Any = None) -> Field:
    """Create a phone field with validation."""
    return Field(
        default=default,
        description=description,
        pattern=r'^\+?[\d\s\-\(\)]{10,15}$'
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