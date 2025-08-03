#!/usr/bin/env python3
"""
Demonstration script for the Dynamic Test Data Factory System.

Shows how to use the TestDataFactory and template system to generate
version-appropriate test data for API testing.
"""

import json
from pathlib import Path

from tests.dynamic.data_factory import get_data_factory
from tests.dynamic.config_manager import get_config_manager
from tests.dynamic.templates import get_template_manager


def demo_basic_data_generation():
    """Demonstrate basic data generation for different versions."""
    print("=== Basic Data Generation Demo ===\n")
    
    factory = get_data_factory()
    
    # Generate pet data for v1
    print("Pet data for v1:")
    pet_v1 = factory.build_pet_data('v1')
    print(json.dumps(pet_v1, indent=2))
    print()
    
    # Generate pet data for v2
    print("Pet data for v2:")
    pet_v2 = factory.build_pet_data('v2')
    print(json.dumps(pet_v2, indent=2))
    print()
    
    # Generate user data for v1
    print("User data for v1:")
    user_v1 = factory.build_user_data('v1')
    print(json.dumps(user_v1, indent=2))
    print()
    
    # Generate user data for v2
    print("User data for v2:")
    user_v2 = factory.build_user_data('v2')
    print(json.dumps(user_v2, indent=2))
    print()


def demo_version_differences():
    """Demonstrate version-specific field differences."""
    print("=== Version Differences Demo ===\n")
    
    factory = get_data_factory()
    
    # Show pet data differences
    pet_v1 = factory.build_pet_data('v1')
    pet_v2 = factory.build_pet_data('v2')
    
    v1_fields = set(pet_v1.keys())
    v2_fields = set(pet_v2.keys())
    
    print("Pet fields in v1:", sorted(v1_fields))
    print("Pet fields in v2:", sorted(v2_fields))
    print("v2-only fields:", sorted(v2_fields - v1_fields))
    print("Common fields:", sorted(v1_fields & v2_fields))
    print()


def demo_relationship_consistency():
    """Demonstrate relationship ID consistency."""
    print("=== Relationship Consistency Demo ===\n")
    
    factory = get_data_factory()
    
    # Generate multiple pets - should have same owner_id
    pet1 = factory.build_pet_data('v1')
    pet2 = factory.build_pet_data('v1')
    
    print(f"Pet 1 owner_id: {pet1['owner_id']}")
    print(f"Pet 2 owner_id: {pet2['owner_id']}")
    print(f"Same owner_id: {pet1['owner_id'] == pet2['owner_id']}")
    print()
    
    # Generate appointment - should use consistent IDs
    appointment = factory.build_appointment_data('v1')
    print(f"Appointment pet_id: {appointment['pet_id']}")
    print(f"Appointment user_id: {appointment['user_id']}")
    print()


def demo_related_data_generation():
    """Demonstrate generating related data with consistent relationships."""
    print("=== Related Data Generation Demo ===\n")
    
    factory = get_data_factory()
    
    # Generate related data for a complete scenario
    relationships = {
        'user': 'owner',
        'pet': 'owned_pet',
        'appointment': 'booking'
    }
    
    related_data = factory.build_related_data('v2', relationships, 
                                            user_email='demo@example.com',
                                            pet_name='Demo Pet')
    
    print("Generated related data:")
    for resource_type, data in related_data.items():
        print(f"\n{resource_type.upper()}:")
        print(json.dumps(data, indent=2))
    print()


def demo_feature_availability():
    """Demonstrate version-specific feature availability."""
    print("=== Feature Availability Demo ===\n")
    
    config_manager = get_config_manager()
    factory = get_data_factory()
    
    features = ['health_records', 'statistics', 'enhanced_filtering', 'batch_operations']
    
    print("Feature availability by version:")
    for version in ['v1', 'v2']:
        print(f"\n{version}:")
        for feature in features:
            available = config_manager.get_feature_availability(version, feature)
            print(f"  {feature}: {'✓' if available else '✗'}")
    
    # Try to generate health record data
    print("\nTrying to generate health record data:")
    try:
        health_record_v1 = factory.build_health_record_data('v1')
        print("v1 health record: SUCCESS")
    except Exception as e:
        print(f"v1 health record: FAILED - {e}")
    
    try:
        health_record_v2 = factory.build_health_record_data('v2')
        print("v2 health record: SUCCESS")
        print(json.dumps(health_record_v2, indent=2))
    except Exception as e:
        print(f"v2 health record: FAILED - {e}")
    print()


def demo_data_validation():
    """Demonstrate data validation capabilities."""
    print("=== Data Validation Demo ===\n")
    
    factory = get_data_factory()
    
    # Generate valid data
    valid_pet = factory.build_pet_data('v1')
    errors = factory.validate_data_against_schema(valid_pet, 'v1', 'pet')
    print(f"Valid pet data validation errors: {len(errors)}")
    
    # Create invalid data
    invalid_pet = {
        'name': 'Test Pet',
        # Missing required fields: species, owner_id
        'email': 'invalid-email',  # Invalid format
        'weight': -5.0,  # Invalid value
        'cost': -10.0   # Invalid value
    }
    
    errors = factory.validate_data_against_schema(invalid_pet, 'v1', 'pet')
    print(f"Invalid pet data validation errors: {len(errors)}")
    for error in errors:
        print(f"  - {error}")
    print()


def demo_custom_overrides():
    """Demonstrate custom field overrides."""
    print("=== Custom Field Overrides Demo ===\n")
    
    factory = get_data_factory()
    
    # Generate pet with custom values
    custom_pet = factory.build_pet_data('v2', 
                                      name='Custom Pet Name',
                                      species='custom_species',
                                      temperament='Very Friendly',
                                      weight=42.5)
    
    print("Pet with custom overrides:")
    print(json.dumps(custom_pet, indent=2))
    print()


def demo_template_vs_direct_generation():
    """Demonstrate template-based vs direct generation."""
    print("=== Template vs Direct Generation Demo ===\n")
    
    factory = get_data_factory()
    
    # Generate using templates
    template_pet = factory.build_pet_data('v2', use_template=True)
    print("Template-based generation:")
    print(json.dumps(template_pet, indent=2))
    print()
    
    # Generate directly
    direct_pet = factory.build_pet_data('v2', use_template=False)
    print("Direct generation:")
    print(json.dumps(direct_pet, indent=2))
    print()


def demo_expected_response_fields():
    """Demonstrate getting expected response fields."""
    print("=== Expected Response Fields Demo ===\n")
    
    factory = get_data_factory()
    
    resources = ['pet', 'user', 'appointment']
    versions = ['v1', 'v2']
    
    for resource in resources:
        print(f"{resource.upper()} response fields:")
        for version in versions:
            fields = factory.get_expected_response_fields(version, resource)
            print(f"  {version}: {len(fields)} fields - {', '.join(fields[:5])}{'...' if len(fields) > 5 else ''}")
        print()


def main():
    """Run all demonstrations."""
    print("Dynamic Test Data Factory System Demo")
    print("=" * 50)
    print()
    
    try:
        demo_basic_data_generation()
        demo_version_differences()
        demo_relationship_consistency()
        demo_related_data_generation()
        demo_feature_availability()
        demo_data_validation()
        demo_custom_overrides()
        demo_template_vs_direct_generation()
        demo_expected_response_fields()
        
        print("Demo completed successfully! ✓")
        
    except Exception as e:
        print(f"Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()