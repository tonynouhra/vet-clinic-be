#!/usr/bin/env python3
"""
Test script to verify database models are working correctly.
"""
import asyncio
import sys
import os
from datetime import datetime, date

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from app.models import (
    User, UserRole, Pet, PetGender, HealthRecord, HealthRecordType,
    Clinic, ClinicType, Veterinarian, Appointment, AppointmentStatus,
    Conversation, ConversationType, Message, MessageType
)


def test_model_imports():
    """Test that all models can be imported successfully."""
    print("✓ All models imported successfully")
    print(f"  - User: {User}")
    print(f"  - Pet: {Pet}")
    print(f"  - Clinic: {Clinic}")
    print(f"  - Veterinarian: {Veterinarian}")
    print(f"  - Appointment: {Appointment}")
    print(f"  - Conversation: {Conversation}")
    print(f"  - Message: {Message}")


def test_model_creation():
    """Test that model instances can be created."""
    try:
        # Test User model
        user = User(
            clerk_id="test_clerk_123",
            email="test@example.com",
            first_name="John",
            last_name="Doe"
        )
        print("✓ User model instance created")
        
        # Test Pet model
        pet = Pet(
            name="Buddy",
            species="Dog",
            breed="Golden Retriever",
            gender=PetGender.MALE,
            birth_date=date(2020, 1, 1)
        )
        print("✓ Pet model instance created")
        
        # Test Clinic model
        clinic = Clinic(
            name="Happy Pets Clinic",
            clinic_type=ClinicType.GENERAL_PRACTICE,
            phone_number="555-0123",
            address_line1="123 Main St",
            city="Anytown",
            state="CA",
            zip_code="12345"
        )
        print("✓ Clinic model instance created")
        
        # Test HealthRecord model
        health_record = HealthRecord(
            record_type=HealthRecordType.VACCINATION,
            title="Annual Vaccination",
            record_date=date.today()
        )
        print("✓ HealthRecord model instance created")
        
        # Test Appointment model
        appointment = Appointment(
            scheduled_at=datetime.now(),
            reason="Annual checkup",
            status=AppointmentStatus.SCHEDULED
        )
        print("✓ Appointment model instance created")
        
        # Test Conversation model
        conversation = Conversation(
            conversation_type=ConversationType.DIRECT_MESSAGE,
            title="Pet Health Discussion"
        )
        print("✓ Conversation model instance created")
        
        # Test Message model
        message = Message(
            message_type=MessageType.TEXT,
            content="Hello, how is my pet doing?"
        )
        print("✓ Message model instance created")
        
        return True
        
    except Exception as e:
        print(f"✗ Model creation failed: {e}")
        return False


def test_model_properties():
    """Test model properties and methods."""
    try:
        # Test User properties
        user = User(
            clerk_id="test_clerk_123",
            email="test@example.com",
            first_name="John",
            last_name="Doe"
        )
        assert user.full_name == "John Doe"
        print("✓ User properties working")
        
        # Test Pet properties
        pet = Pet(
            name="Buddy",
            species="Dog",
            breed="Golden Retriever",
            gender=PetGender.MALE,
            birth_date=date(2020, 1, 1),
            age_years=4,
            age_months=2
        )
        assert "4 years, 2 months" in pet.age_display
        print("✓ Pet properties working")
        
        # Test Clinic properties
        clinic = Clinic(
            name="Happy Pets Clinic",
            clinic_type=ClinicType.GENERAL_PRACTICE,
            phone_number="555-0123",
            address_line1="123 Main St",
            city="Anytown",
            state="CA",
            zip_code="12345"
        )
        assert "123 Main St, Anytown, CA, 12345" in clinic.full_address
        print("✓ Clinic properties working")
        
        # Test Appointment properties
        appointment = Appointment(
            scheduled_at=datetime.now(),
            reason="Annual checkup",
            status=AppointmentStatus.SCHEDULED
        )
        assert appointment.can_be_cancelled == True
        print("✓ Appointment properties working")
        
        return True
        
    except Exception as e:
        print(f"✗ Model properties test failed: {e}")
        return False


def test_enum_values():
    """Test that enum values are working correctly."""
    try:
        # Test UserRole enum
        assert UserRole.PET_OWNER == "pet_owner"
        assert UserRole.VETERINARIAN == "veterinarian"
        print("✓ UserRole enum working")
        
        # Test PetGender enum
        assert PetGender.MALE == "male"
        assert PetGender.FEMALE == "female"
        print("✓ PetGender enum working")
        
        # Test ClinicType enum
        assert ClinicType.GENERAL_PRACTICE == "general_practice"
        assert ClinicType.EMERGENCY_CLINIC == "emergency_clinic"
        print("✓ ClinicType enum working")
        
        # Test AppointmentStatus enum
        assert AppointmentStatus.SCHEDULED == "scheduled"
        assert AppointmentStatus.COMPLETED == "completed"
        print("✓ AppointmentStatus enum working")
        
        return True
        
    except Exception as e:
        print(f"✗ Enum values test failed: {e}")
        return False


def main():
    """Run all model tests."""
    print("Testing Veterinary Clinic Database Models")
    print("=" * 50)
    
    # Test model imports
    test_model_imports()
    
    # Test model creation
    creation_ok = test_model_creation()
    
    # Test model properties
    properties_ok = test_model_properties()
    
    # Test enum values
    enums_ok = test_enum_values()
    
    print("\n" + "=" * 50)
    print("Model Test Summary:")
    print("✓ Model imports: OK")
    print(f"{'✓' if creation_ok else '✗'} Model creation: {'OK' if creation_ok else 'FAILED'}")
    print(f"{'✓' if properties_ok else '✗'} Model properties: {'OK' if properties_ok else 'FAILED'}")
    print(f"{'✓' if enums_ok else '✗'} Enum values: {'OK' if enums_ok else 'FAILED'}")
    
    if creation_ok and properties_ok and enums_ok:
        print("\n🎉 All model tests passed! Database models are working correctly.")
        return 0
    else:
        print("\n❌ Some model tests failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())