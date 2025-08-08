#!/usr/bin/env python3
"""
Test script to verify pet management implementation.

This script tests the core functionality of the pet management system
including health records, reminders, and notification services.
"""

import asyncio
import uuid
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

# Test imports
def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports...")
    
    try:
        from app.pets.services import PetService
        from app.pets.controller import PetController
        from app.services.notification_service import NotificationService
        from app.models.pet import Pet, PetGender, PetSize, HealthRecord, HealthRecordType, Reminder
        from app.api.schemas.v1.pets import (
            PetCreateV1, PetUpdateV1, PetResponseV1,
            HealthRecordCreateV1, HealthRecordResponseV1,
            ReminderCreateV1, ReminderResponseV1
        )
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False


def test_model_creation():
    """Test that models can be created."""
    print("\nTesting model creation...")
    
    try:
        from app.models.pet import Pet, PetGender, PetSize, HealthRecord, HealthRecordType, Reminder
        # Test Pet model
        pet = Pet(
            id=uuid.uuid4(),
            owner_id=uuid.uuid4(),
            name="Buddy",
            species="dog",
            breed="Golden Retriever",
            gender=PetGender.MALE,
            size=PetSize.LARGE,
            weight=65.5,
            is_active=True,
            is_deceased=False,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        assert pet.name == "Buddy"
        assert pet.species == "dog"
        print("✅ Pet model creation successful")
        
        # Test HealthRecord model
        health_record = HealthRecord(
            id=uuid.uuid4(),
            pet_id=pet.id,
            record_type=HealthRecordType.VACCINATION,
            title="Annual Rabies Vaccination",
            description="Rabies vaccination administered",
            record_date=date(2024, 1, 15),
            next_due_date=date(2025, 1, 15),
            medication_name="Rabies Vaccine",
            dosage="1ml",
            cost=45.00,
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        assert health_record.title == "Annual Rabies Vaccination"
        assert health_record.record_type == HealthRecordType.VACCINATION
        print("✅ HealthRecord model creation successful")
        
        # Test Reminder model
        reminder = Reminder(
            id=uuid.uuid4(),
            pet_id=pet.id,
            title="Vaccination Reminder",
            description="Time for annual rabies vaccination",
            reminder_type="vaccination",
            due_date=date(2025, 1, 15),
            reminder_date=date(2025, 1, 8),
            is_recurring=False,
            is_completed=False,
            is_sent=False,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        assert reminder.title == "Vaccination Reminder"
        assert reminder.reminder_type == "vaccination"
        print("✅ Reminder model creation successful")
        
        return True
    except Exception as e:
        print(f"❌ Model creation error: {e}")
        return False


def test_schema_validation():
    """Test that schemas can validate data."""
    print("\nTesting schema validation...")
    
    try:
        from app.api.schemas.v1.pets import (
            PetCreateV1, HealthRecordCreateV1, ReminderCreateV1
        )
        from app.models.pet import HealthRecordType
        
        # Test PetCreateV1 schema
        pet_data = {
            "owner_id": str(uuid.uuid4()),
            "name": "Buddy",
            "species": "dog",
            "breed": "Golden Retriever",
            "gender": "male",
            "size": "large",
            "weight": 65.5,
            "birth_date": "2020-01-15"
        }
        pet_schema = PetCreateV1(**pet_data)
        assert pet_schema.name == "Buddy"
        assert pet_schema.species == "dog"
        print("✅ PetCreateV1 schema validation successful")
        
        # Test HealthRecordCreateV1 schema
        health_record_data = {
            "record_type": "vaccination",
            "title": "Annual Rabies Vaccination",
            "description": "Rabies vaccination administered",
            "record_date": "2024-01-15",
            "next_due_date": "2025-01-15",
            "medication_name": "Rabies Vaccine",
            "dosage": "1ml",
            "cost": 45.00
        }
        health_record_schema = HealthRecordCreateV1(**health_record_data)
        assert health_record_schema.title == "Annual Rabies Vaccination"
        assert health_record_schema.record_type == HealthRecordType.VACCINATION
        print("✅ HealthRecordCreateV1 schema validation successful")
        
        # Test ReminderCreateV1 schema
        reminder_data = {
            "title": "Vaccination Reminder",
            "description": "Time for annual rabies vaccination",
            "reminder_type": "vaccination",
            "due_date": "2025-01-15",
            "reminder_date": "2025-01-08",
            "is_recurring": False
        }
        reminder_schema = ReminderCreateV1(**reminder_data)
        assert reminder_schema.title == "Vaccination Reminder"
        assert reminder_schema.reminder_type == "vaccination"
        print("✅ ReminderCreateV1 schema validation successful")
        
        return True
    except Exception as e:
        print(f"❌ Schema validation error: {e}")
        return False


async def test_service_methods():
    """Test service methods with mocked database."""
    print("\nTesting service methods...")
    
    try:
        from app.pets.services import PetService
        
        # Create mock database session
        mock_db = AsyncMock()
        pet_service = PetService(mock_db)
        
        # Test that service can be instantiated
        assert pet_service.db == mock_db
        print("✅ PetService instantiation successful")
        
        # Test method signatures exist
        assert hasattr(pet_service, 'create_pet')
        assert hasattr(pet_service, 'get_pet_by_id')
        assert hasattr(pet_service, 'add_health_record')
        assert hasattr(pet_service, 'create_reminder')
        assert hasattr(pet_service, 'get_pet_health_records')
        assert hasattr(pet_service, 'get_pet_reminders')
        print("✅ All required service methods exist")
        
        return True
    except Exception as e:
        print(f"❌ Service method error: {e}")
        return False


def test_notification_service():
    """Test notification service functionality."""
    print("\nTesting notification service...")
    
    try:
        from app.services.notification_service import NotificationService
        from app.models.user import User, UserRole
        from app.models.pet import Pet, PetGender, PetSize, Reminder
        
        # Create notification service
        notification_service = NotificationService()
        assert notification_service is not None
        print("✅ NotificationService instantiation successful")
        
        # Test method signatures exist
        assert hasattr(notification_service, 'send_reminder_notification')
        assert hasattr(notification_service, 'send_appointment_reminder')
        assert hasattr(notification_service, 'send_health_alert')
        print("✅ All required notification methods exist")
        
        # Test message formatting
        mock_user = User(
            id=uuid.uuid4(),
            email="owner@example.com",
            first_name="John",
            last_name="Doe",
            role=UserRole.PET_OWNER,
            is_active=True
        )
        
        mock_pet = Pet(
            id=uuid.uuid4(),
            owner_id=mock_user.id,
            name="Buddy",
            species="dog",
            breed="Golden Retriever",
            gender=PetGender.MALE,
            size=PetSize.LARGE,
            weight=65.5,
            is_active=True,
            is_deceased=False,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        mock_reminder = Reminder(
            id=uuid.uuid4(),
            pet_id=mock_pet.id,
            title="Vaccination Reminder",
            description="Time for annual rabies vaccination",
            reminder_type="vaccination",
            due_date=date(2025, 1, 15),
            reminder_date=date(2025, 1, 8),
            is_recurring=False,
            is_completed=False,
            is_sent=False,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Test message formatting
        message = notification_service._format_reminder_message(
            user=mock_user,
            pet=mock_pet,
            reminder=mock_reminder
        )
        
        assert "Hello John" in message
        assert "Buddy" in message
        assert "Vaccination Reminder" in message
        print("✅ Message formatting successful")
        
        return True
    except Exception as e:
        print(f"❌ Notification service error: {e}")
        return False


def test_controller_instantiation():
    """Test controller instantiation."""
    print("\nTesting controller instantiation...")
    
    try:
        from app.pets.controller import PetController
        
        # Create mock database session
        mock_db = AsyncMock()
        
        # Test that controller can be instantiated
        controller = PetController(mock_db)
        assert controller.db == mock_db
        assert controller.service is not None
        print("✅ PetController instantiation successful")
        
        # Test method signatures exist
        assert hasattr(controller, 'create_pet')
        assert hasattr(controller, 'get_pet_by_id')
        assert hasattr(controller, 'add_health_record')
        assert hasattr(controller, 'create_reminder')
        assert hasattr(controller, 'get_pet_health_records')
        assert hasattr(controller, 'get_pet_reminders')
        print("✅ All required controller methods exist")
        
        return True
    except Exception as e:
        print(f"❌ Controller instantiation error: {e}")
        return False


async def main():
    """Run all tests."""
    print("🧪 Testing Pet Management Implementation")
    print("=" * 50)
    
    tests = [
        ("Imports", test_imports),
        ("Model Creation", test_model_creation),
        ("Schema Validation", test_schema_validation),
        ("Service Methods", test_service_methods),
        ("Notification Service", test_notification_service),
        ("Controller Instantiation", test_controller_instantiation),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            if result:
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Pet management implementation is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)