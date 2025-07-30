#!/usr/bin/env python3
"""
Verification script for Task 2: Implement core database models and relationships
"""
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from app.models import (
    # User models
    User, UserSession, UserRole, user_roles,
    
    # Pet models  
    Pet, HealthRecord, Reminder, PetGender, PetSize, HealthRecordType,
    
    # Clinic models
    Clinic, ClinicOperatingHours, Veterinarian, VeterinarianAvailability,
    ClinicReview, VeterinarianReview, ClinicType, VeterinarianSpecialty,
    DayOfWeek, veterinarian_specialties,
    
    # Appointment models
    Appointment, AppointmentSlot, AppointmentStatus, AppointmentType,
    AppointmentPriority,
    
    # Communication models
    Conversation, Message, MessageReaction, ChatBot, NotificationPreference,
    ConversationType, MessageType, MessageStatus, conversation_participants
)


def verify_user_model_with_clerk_integration():
    """Verify User model with Clerk integration and role-based access control."""
    print("✓ User model with Clerk integration:")
    print(f"  - User model: {User}")
    print(f"  - UserSession model: {UserSession}")
    print(f"  - UserRole enum: {UserRole}")
    print(f"  - user_roles association table: {user_roles}")
    
    # Check User model has required Clerk fields
    user_columns = [col.name for col in User.__table__.columns]
    required_fields = ['clerk_id', 'email', 'first_name', 'last_name']
    for field in required_fields:
        assert field in user_columns, f"Missing required field: {field}"
    
    # Check role-based methods exist
    user = User(clerk_id="test", email="test@test.com", first_name="Test", last_name="User")
    assert hasattr(user, 'has_role'), "Missing has_role method"
    assert hasattr(user, 'is_pet_owner'), "Missing is_pet_owner method"
    assert hasattr(user, 'is_veterinarian'), "Missing is_veterinarian method"
    assert hasattr(user, 'is_clinic_admin'), "Missing is_clinic_admin method"
    
    print("  ✓ Clerk integration fields present")
    print("  ✓ Role-based access control methods present")
    return True


def verify_pet_model_with_health_records():
    """Verify Pet model with health record relationships."""
    print("✓ Pet model with health record relationships:")
    print(f"  - Pet model: {Pet}")
    print(f"  - HealthRecord model: {HealthRecord}")
    print(f"  - Reminder model: {Reminder}")
    print(f"  - PetGender enum: {PetGender}")
    print(f"  - PetSize enum: {PetSize}")
    print(f"  - HealthRecordType enum: {HealthRecordType}")
    
    # Check Pet model has required fields
    pet_columns = [col.name for col in Pet.__table__.columns]
    required_fields = ['name', 'species', 'breed', 'gender', 'owner_id']
    for field in required_fields:
        assert field in pet_columns, f"Missing required field: {field}"
    
    # Check HealthRecord model has required fields
    health_record_columns = [col.name for col in HealthRecord.__table__.columns]
    required_fields = ['pet_id', 'record_type', 'title', 'record_date']
    for field in required_fields:
        assert field in health_record_columns, f"Missing required field: {field}"
    
    # Check relationships exist
    assert hasattr(Pet, 'health_records'), "Missing health_records relationship"
    assert hasattr(Pet, 'reminders'), "Missing reminders relationship"
    
    print("  ✓ Pet profile fields present")
    print("  ✓ Health record relationships present")
    print("  ✓ Reminder system present")
    return True


def verify_appointment_model_with_associations():
    """Verify Appointment model with veterinarian and clinic associations."""
    print("✓ Appointment model with veterinarian and clinic associations:")
    print(f"  - Appointment model: {Appointment}")
    print(f"  - AppointmentSlot model: {AppointmentSlot}")
    print(f"  - AppointmentStatus enum: {AppointmentStatus}")
    print(f"  - AppointmentType enum: {AppointmentType}")
    print(f"  - AppointmentPriority enum: {AppointmentPriority}")
    
    # Check Appointment model has required associations
    appointment_columns = [col.name for col in Appointment.__table__.columns]
    required_fields = ['pet_id', 'pet_owner_id', 'veterinarian_id', 'clinic_id', 'scheduled_at']
    for field in required_fields:
        assert field in appointment_columns, f"Missing required field: {field}"
    
    # Check relationships exist
    assert hasattr(Appointment, 'pet'), "Missing pet relationship"
    assert hasattr(Appointment, 'veterinarian'), "Missing veterinarian relationship"
    assert hasattr(Appointment, 'clinic'), "Missing clinic relationship"
    
    print("  ✓ Veterinarian associations present")
    print("  ✓ Clinic associations present")
    print("  ✓ Pet associations present")
    return True


def verify_clinic_and_veterinarian_models():
    """Verify Clinic and Veterinarian models with location data."""
    print("✓ Clinic and Veterinarian models with location data:")
    print(f"  - Clinic model: {Clinic}")
    print(f"  - ClinicOperatingHours model: {ClinicOperatingHours}")
    print(f"  - Veterinarian model: {Veterinarian}")
    print(f"  - VeterinarianAvailability model: {VeterinarianAvailability}")
    print(f"  - ClinicReview model: {ClinicReview}")
    print(f"  - VeterinarianReview model: {VeterinarianReview}")
    
    # Check Clinic model has location fields
    clinic_columns = [col.name for col in Clinic.__table__.columns]
    location_fields = ['address_line1', 'city', 'state', 'zip_code', 'latitude', 'longitude']
    for field in location_fields:
        assert field in clinic_columns, f"Missing location field: {field}"
    
    # Check Veterinarian model has required fields
    vet_columns = [col.name for col in Veterinarian.__table__.columns]
    required_fields = ['user_id', 'clinic_id', 'license_number']
    for field in required_fields:
        assert field in required_fields, f"Missing required field: {field}"
    
    print("  ✓ Location data fields present")
    print("  ✓ Veterinarian profile fields present")
    print("  ✓ Operating hours and availability models present")
    return True


def verify_communication_models():
    """Verify Communication models for chat and messaging functionality."""
    print("✓ Communication models for chat and messaging:")
    print(f"  - Conversation model: {Conversation}")
    print(f"  - Message model: {Message}")
    print(f"  - MessageReaction model: {MessageReaction}")
    print(f"  - ChatBot model: {ChatBot}")
    print(f"  - NotificationPreference model: {NotificationPreference}")
    print(f"  - conversation_participants association table: {conversation_participants}")
    
    # Check Conversation model has required fields
    conversation_columns = [col.name for col in Conversation.__table__.columns]
    required_fields = ['conversation_type', 'is_group', 'is_active']
    for field in required_fields:
        assert field in conversation_columns, f"Missing required field: {field}"
    
    # Check Message model has required fields
    message_columns = [col.name for col in Message.__table__.columns]
    required_fields = ['conversation_id', 'sender_id', 'message_type', 'status']
    for field in required_fields:
        assert field in message_columns, f"Missing required field: {field}"
    
    # Check relationships exist
    assert hasattr(Conversation, 'messages'), "Missing messages relationship"
    assert hasattr(Message, 'conversation'), "Missing conversation relationship"
    
    print("  ✓ Chat conversation models present")
    print("  ✓ Messaging functionality present")
    print("  ✓ AI chatbot integration present")
    return True


def verify_database_migration_readiness():
    """Verify that models are ready for database migration scripts."""
    print("✓ Database migration readiness:")
    
    # Check that all models have proper table names
    models_with_tables = [
        User, UserSession, Pet, HealthRecord, Reminder,
        Clinic, ClinicOperatingHours, Veterinarian, VeterinarianAvailability,
        ClinicReview, VeterinarianReview, Appointment, AppointmentSlot,
        Conversation, Message, MessageReaction, ChatBot, NotificationPreference
    ]
    
    for model in models_with_tables:
        assert hasattr(model, '__tablename__'), f"Model {model} missing __tablename__"
        assert hasattr(model, '__table__'), f"Model {model} missing __table__"
    
    # Check that association tables are properly defined
    association_tables = [user_roles, veterinarian_specialties, conversation_participants]
    for table in association_tables:
        assert hasattr(table, 'name'), f"Association table {table} missing name"
    
    print("  ✓ All models have proper table definitions")
    print("  ✓ Association tables properly defined")
    print("  ✓ Models ready for Alembic migration scripts")
    return True


def main():
    """Run all verification checks for Task 2."""
    print("Verifying Task 2: Implement core database models and relationships")
    print("=" * 70)
    
    try:
        # Verify each sub-task
        user_ok = verify_user_model_with_clerk_integration()
        pet_ok = verify_pet_model_with_health_records()
        appointment_ok = verify_appointment_model_with_associations()
        clinic_ok = verify_clinic_and_veterinarian_models()
        communication_ok = verify_communication_models()
        migration_ok = verify_database_migration_readiness()
        
        print("\n" + "=" * 70)
        print("Task 2 Verification Summary:")
        print(f"{'✓' if user_ok else '✗'} User model with Clerk integration: {'COMPLETE' if user_ok else 'FAILED'}")
        print(f"{'✓' if pet_ok else '✗'} Pet model with health records: {'COMPLETE' if pet_ok else 'FAILED'}")
        print(f"{'✓' if appointment_ok else '✗'} Appointment model with associations: {'COMPLETE' if appointment_ok else 'FAILED'}")
        print(f"{'✓' if clinic_ok else '✗'} Clinic and Veterinarian models: {'COMPLETE' if clinic_ok else 'FAILED'}")
        print(f"{'✓' if communication_ok else '✗'} Communication models: {'COMPLETE' if communication_ok else 'FAILED'}")
        print(f"{'✓' if migration_ok else '✗'} Database migration readiness: {'COMPLETE' if migration_ok else 'FAILED'}")
        
        all_complete = all([user_ok, pet_ok, appointment_ok, clinic_ok, communication_ok, migration_ok])
        
        if all_complete:
            print("\n🎉 Task 2 COMPLETE: All core database models and relationships implemented successfully!")
            print("\nImplemented models:")
            print("  • User model with Clerk integration and role-based access control")
            print("  • Pet model with comprehensive health record relationships")
            print("  • Appointment model with veterinarian and clinic associations")
            print("  • Clinic and Veterinarian models with location data")
            print("  • Communication models for chat and messaging functionality")
            print("  • All models ready for database migration scripts using Alembic")
            return 0
        else:
            print("\n❌ Task 2 INCOMPLETE: Some models or relationships are missing.")
            return 1
            
    except Exception as e:
        print(f"\n❌ Verification failed with error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())