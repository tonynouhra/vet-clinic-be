#!/usr/bin/env python3
"""
Test script to verify database models are working correctly.
"""
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

def test_model_imports():
    """Test that all models can be imported successfully."""
    try:
        print("Testing model imports...")
        
        # Test user models
        from app.models.user import User, UserSession, UserRole
        print("✓ User models imported successfully")
        
        # Test pet models
        from app.models.pet import Pet, HealthRecord, Reminder, PetGender, PetSize, HealthRecordType
        print("✓ Pet models imported successfully")
        
        # Test clinic models
        from app.models.clinic import (
            Clinic, ClinicOperatingHours, Veterinarian, VeterinarianAvailability,
            ClinicReview, VeterinarianReview, ClinicType, VeterinarianSpecialty, DayOfWeek
        )
        print("✓ Clinic models imported successfully")
        
        # Test appointment models
        from app.models.appointment import (
            Appointment, AppointmentSlot, AppointmentStatus, AppointmentType, AppointmentPriority
        )
        print("✓ Appointment models imported successfully")
        
        # Test communication models
        from app.models.communication import (
            Conversation, Message, MessageReaction, ChatBot, NotificationPreference,
            ConversationType, MessageType, MessageStatus
        )
        print("✓ Communication models imported successfully")
        
        # Test models package import
        from app.models import (
            User, Pet, Clinic, Veterinarian, Appointment, Conversation, Message
        )
        print("✓ Models package imported successfully")
        
        print("\n🎉 All model imports successful!")
        return True
        
    except Exception as e:
        print(f"❌ Error importing models: {e}")
        return False


def test_enum_values():
    """Test that enum values are correctly defined."""
    try:
        print("\nTesting enum values...")
        
        from app.models.user import UserRole
        from app.models.pet import PetGender, PetSize, HealthRecordType
        from app.models.clinic import ClinicType, VeterinarianSpecialty, DayOfWeek
        from app.models.appointment import AppointmentStatus, AppointmentType, AppointmentPriority
        from app.models.communication import ConversationType, MessageType, MessageStatus
        
        # Test UserRole enum
        assert UserRole.PET_OWNER == "pet_owner"
        assert UserRole.VETERINARIAN == "veterinarian"
        assert UserRole.CLINIC_ADMIN == "clinic_admin"
        assert UserRole.SYSTEM_ADMIN == "system_admin"
        print("✓ UserRole enum values correct")
        
        # Test PetGender enum
        assert PetGender.MALE == "male"
        assert PetGender.FEMALE == "female"
        assert PetGender.UNKNOWN == "unknown"
        print("✓ PetGender enum values correct")
        
        # Test AppointmentStatus enum
        assert AppointmentStatus.SCHEDULED == "scheduled"
        assert AppointmentStatus.CONFIRMED == "confirmed"
        assert AppointmentStatus.COMPLETED == "completed"
        print("✓ AppointmentStatus enum values correct")
        
        # Test MessageType enum
        assert MessageType.TEXT == "text"
        assert MessageType.IMAGE == "image"
        assert MessageType.AI_RESPONSE == "ai_response"
        print("✓ MessageType enum values correct")
        
        print("\n🎉 All enum values are correct!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing enum values: {e}")
        return False


def test_model_relationships():
    """Test that model relationships are properly defined."""
    try:
        print("\nTesting model relationships...")
        
        from app.models.user import User
        from app.models.pet import Pet
        from app.models.clinic import Clinic, Veterinarian
        from app.models.appointment import Appointment
        from app.models.communication import Conversation, Message
        
        # Test User model relationships
        user_relationships = ['pets', 'appointments', 'veterinarian_profile', 'conversations', 'messages_sent']
        for rel in user_relationships:
            assert hasattr(User, rel), f"User missing relationship: {rel}"
        print("✓ User relationships defined")
        
        # Test Pet model relationships
        pet_relationships = ['owner', 'health_records', 'appointments', 'reminders']
        for rel in pet_relationships:
            assert hasattr(Pet, rel), f"Pet missing relationship: {rel}"
        print("✓ Pet relationships defined")
        
        # Test Veterinarian model relationships
        vet_relationships = ['user', 'clinic', 'appointments', 'availability', 'reviews', 'health_records']
        for rel in vet_relationships:
            assert hasattr(Veterinarian, rel), f"Veterinarian missing relationship: {rel}"
        print("✓ Veterinarian relationships defined")
        
        # Test Appointment model relationships
        appointment_relationships = ['pet', 'pet_owner', 'veterinarian', 'clinic']
        for rel in appointment_relationships:
            assert hasattr(Appointment, rel), f"Appointment missing relationship: {rel}"
        print("✓ Appointment relationships defined")
        
        # Test Message model relationships
        message_relationships = ['conversation', 'sender', 'reply_to', 'reactions']
        for rel in message_relationships:
            assert hasattr(Message, rel), f"Message missing relationship: {rel}"
        print("✓ Message relationships defined")
        
        print("\n🎉 All model relationships are properly defined!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing model relationships: {e}")
        return False


def test_model_methods():
    """Test that model methods are working correctly."""
    try:
        print("\nTesting model methods...")
        
        from app.models.user import User, UserRole
        from app.models.pet import Pet
        from app.models.appointment import Appointment, AppointmentStatus
        
        # Test User methods (without database)
        user = User()
        user.first_name = "John"
        user.last_name = "Doe"
        assert user.full_name == "John Doe"
        print("✓ User.full_name property works")
        
        # Test Pet age display property (without database)
        pet = Pet()
        pet.age_years = 3
        pet.age_months = 6
        assert "3 years, 6 months" in pet.age_display
        print("✓ Pet.age_display property works")
        
        # Test Appointment status methods (without database)
        appointment = Appointment()
        appointment.status = AppointmentStatus.SCHEDULED
        assert appointment.can_be_cancelled == True
        assert appointment.can_be_rescheduled == True
        print("✓ Appointment status methods work")
        
        print("\n🎉 All model methods are working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing model methods: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("VETERINARY CLINIC PLATFORM - DATABASE MODELS TEST")
    print("=" * 60)
    
    tests = [
        test_model_imports,
        test_enum_values,
        test_model_relationships,
        test_model_methods
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 60)
    print(f"TEST RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Database models are ready for use.")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())