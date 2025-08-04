"""
Unit tests for Clerk schemas and data models.
"""
import pytest
from datetime import datetime
from typing import Dict, Any

from app.schemas.clerk_schemas import (
    ClerkUser,
    ClerkEmailAddress,
    ClerkPhoneNumber,
    ClerkRoleMapping,
    ClerkUserTransform,
    ClerkUserValidation,
    ClerkWebhookEvent,
    ClerkUserSyncRequest,
    ClerkUserSyncResponse,
    ClerkTokenValidationRequest,
    ClerkTokenValidationResponse,
)
from app.models.user import UserRole


class TestClerkEmailAddress:
    """Test ClerkEmailAddress schema."""
    
    def test_valid_email_address(self):
        """Test valid email address creation."""
        email_data = {
            "id": "email_123",
            "email_address": "test@example.com",
            "verification": {"status": "verified"},
            "linked_to": []
        }
        
        email = ClerkEmailAddress(**email_data)
        assert email.id == "email_123"
        assert email.email_address == "test@example.com"
        assert email.verification["status"] == "verified"
    
    def test_minimal_email_address(self):
        """Test email address with minimal required fields."""
        email_data = {
            "id": "email_123",
            "email_address": "test@example.com"
        }
        
        email = ClerkEmailAddress(**email_data)
        assert email.id == "email_123"
        assert email.email_address == "test@example.com"
        assert email.verification is None
        assert email.linked_to is None


class TestClerkPhoneNumber:
    """Test ClerkPhoneNumber schema."""
    
    def test_valid_phone_number(self):
        """Test valid phone number creation."""
        phone_data = {
            "id": "phone_123",
            "phone_number": "+1234567890",
            "verification": {"status": "verified"},
            "linked_to": []
        }
        
        phone = ClerkPhoneNumber(**phone_data)
        assert phone.id == "phone_123"
        assert phone.phone_number == "+1234567890"
        assert phone.verification["status"] == "verified"
    
    def test_minimal_phone_number(self):
        """Test phone number with minimal required fields."""
        phone_data = {
            "id": "phone_123",
            "phone_number": "+1234567890"
        }
        
        phone = ClerkPhoneNumber(**phone_data)
        assert phone.id == "phone_123"
        assert phone.phone_number == "+1234567890"
        assert phone.verification is None
        assert phone.linked_to is None


class TestClerkUser:
    """Test ClerkUser schema."""
    
    @pytest.fixture
    def sample_clerk_user_data(self) -> Dict[str, Any]:
        """Sample Clerk user data for testing."""
        return {
            "id": "user_123",
            "email_addresses": [
                {
                    "id": "email_123",
                    "email_address": "john.doe@example.com",
                    "verification": {"status": "verified"}
                }
            ],
            "phone_numbers": [
                {
                    "id": "phone_123",
                    "phone_number": "+1234567890",
                    "verification": {"status": "verified"}
                }
            ],
            "first_name": "John",
            "last_name": "Doe",
            "image_url": "https://example.com/avatar.jpg",
            "has_image": True,
            "public_metadata": {"role": "veterinarian"},
            "private_metadata": {"preferences": {"theme": "dark"}},
            "unsafe_metadata": {},
            "created_at": 1640995200000,  # 2022-01-01 00:00:00 UTC
            "updated_at": 1640995200000,
            "last_sign_in_at": 1640995200000,
            "banned": False,
            "locked": False,
            "verification_attempts_remaining": 3
        }
    
    def test_valid_clerk_user(self, sample_clerk_user_data):
        """Test valid ClerkUser creation."""
        user = ClerkUser(**sample_clerk_user_data)
        
        assert user.id == "user_123"
        assert user.first_name == "John"
        assert user.last_name == "Doe"
        assert user.primary_email == "john.doe@example.com"
        assert user.primary_phone == "+1234567890"
        assert user.public_metadata["role"] == "veterinarian"
        assert not user.banned
        assert not user.locked
    
    def test_minimal_clerk_user(self):
        """Test ClerkUser with minimal required fields."""
        minimal_data = {
            "id": "user_123",
            "created_at": 1640995200000,
            "updated_at": 1640995200000
        }
        
        user = ClerkUser(**minimal_data)
        assert user.id == "user_123"
        assert user.primary_email is None
        assert user.primary_phone is None
        assert len(user.email_addresses) == 0
        assert len(user.phone_numbers) == 0
    
    def test_datetime_properties(self, sample_clerk_user_data):
        """Test datetime property conversions."""
        user = ClerkUser(**sample_clerk_user_data)
        
        expected_datetime = datetime(2022, 1, 1, 0, 0, 0)
        assert user.created_at_datetime.replace(microsecond=0) == expected_datetime
        assert user.updated_at_datetime.replace(microsecond=0) == expected_datetime
        assert user.last_sign_in_datetime.replace(microsecond=0) == expected_datetime
    
    def test_no_last_sign_in(self, sample_clerk_user_data):
        """Test user with no last sign in."""
        sample_clerk_user_data["last_sign_in_at"] = None
        user = ClerkUser(**sample_clerk_user_data)
        
        assert user.last_sign_in_datetime is None


class TestClerkRoleMapping:
    """Test ClerkRoleMapping functionality."""
    
    def test_default_role_mapping(self):
        """Test default role mapping configuration."""
        mapping = ClerkRoleMapping()
        
        assert mapping.get_internal_role("admin") == UserRole.ADMIN
        assert mapping.get_internal_role("veterinarian") == UserRole.VETERINARIAN
        assert mapping.get_internal_role("receptionist") == UserRole.RECEPTIONIST
        assert mapping.get_internal_role("clinic_manager") == UserRole.CLINIC_MANAGER
        assert mapping.get_internal_role("pet_owner") == UserRole.PET_OWNER
        assert mapping.get_internal_role("staff") == UserRole.RECEPTIONIST
    
    def test_case_insensitive_mapping(self):
        """Test case insensitive role mapping."""
        mapping = ClerkRoleMapping()
        
        assert mapping.get_internal_role("ADMIN") == UserRole.ADMIN
        assert mapping.get_internal_role("Admin") == UserRole.ADMIN
        assert mapping.get_internal_role("VETERINARIAN") == UserRole.VETERINARIAN
    
    def test_unknown_role_default(self):
        """Test unknown role returns default."""
        mapping = ClerkRoleMapping()
        
        assert mapping.get_internal_role("unknown_role") == UserRole.PET_OWNER
        assert mapping.get_internal_role(None) == UserRole.PET_OWNER
        assert mapping.get_internal_role("") == UserRole.PET_OWNER
    
    def test_custom_role_mapping(self):
        """Test custom role mapping configuration."""
        custom_mappings = {
            "doctor": UserRole.VETERINARIAN,
            "nurse": UserRole.RECEPTIONIST,
            "owner": UserRole.PET_OWNER
        }
        
        mapping = ClerkRoleMapping(
            mappings=custom_mappings,
            default_role=UserRole.RECEPTIONIST
        )
        
        assert mapping.get_internal_role("doctor") == UserRole.VETERINARIAN
        assert mapping.get_internal_role("nurse") == UserRole.RECEPTIONIST
        assert mapping.get_internal_role("unknown") == UserRole.RECEPTIONIST


class TestClerkUserTransform:
    """Test ClerkUserTransform functionality."""
    
    @pytest.fixture
    def sample_clerk_user(self) -> ClerkUser:
        """Sample ClerkUser for testing."""
        return ClerkUser(
            id="user_123",
            email_addresses=[
                ClerkEmailAddress(id="email_123", email_address="john.doe@example.com")
            ],
            phone_numbers=[
                ClerkPhoneNumber(id="phone_123", phone_number="+1234567890")
            ],
            first_name="John",
            last_name="Doe",
            image_url="https://example.com/avatar.jpg",
            public_metadata={"role": "veterinarian"},
            private_metadata={
                "preferences": {"theme": "dark"},
                "notifications": {"email": True},
                "timezone": "America/New_York",
                "language": "en"
            },
            created_at=1640995200000,
            updated_at=1640995200000,
            banned=False,
            locked=False
        )
    
    @pytest.fixture
    def role_mapping(self) -> ClerkRoleMapping:
        """Role mapping for testing."""
        return ClerkRoleMapping()
    
    def test_to_user_create_data(self, sample_clerk_user, role_mapping):
        """Test transformation to user creation data."""
        create_data = ClerkUserTransform.to_user_create_data(sample_clerk_user, role_mapping)
        
        assert create_data["clerk_id"] == "user_123"
        assert create_data["email"] == "john.doe@example.com"
        assert create_data["first_name"] == "John"
        assert create_data["last_name"] == "Doe"
        assert create_data["phone_number"] == "+1234567890"
        assert create_data["role"] == UserRole.VETERINARIAN
        assert create_data["avatar_url"] == "https://example.com/avatar.jpg"
        assert create_data["is_active"] is True
        assert create_data["is_verified"] is True
        assert create_data["preferences"] == {"theme": "dark"}
        assert create_data["notification_settings"] == {"email": True}
        assert create_data["timezone"] == "America/New_York"
        assert create_data["language"] == "en"
    
    def test_to_user_create_data_minimal(self, role_mapping):
        """Test transformation with minimal user data."""
        minimal_user = ClerkUser(
            id="user_123",
            created_at=1640995200000,
            updated_at=1640995200000
        )
        
        create_data = ClerkUserTransform.to_user_create_data(minimal_user, role_mapping)
        
        assert create_data["clerk_id"] == "user_123"
        assert create_data["email"] is None
        assert create_data["first_name"] == ""
        assert create_data["last_name"] == ""
        assert create_data["phone_number"] is None
        assert create_data["role"] == UserRole.PET_OWNER  # Default role
        assert create_data["is_active"] is True  # Not banned or locked
    
    def test_to_user_update_data(self, sample_clerk_user, role_mapping):
        """Test transformation to user update data."""
        update_data = ClerkUserTransform.to_user_update_data(sample_clerk_user, role_mapping)
        
        assert update_data["email"] == "john.doe@example.com"
        assert update_data["first_name"] == "John"
        assert update_data["last_name"] == "Doe"
        assert update_data["phone_number"] == "+1234567890"
        assert update_data["role"] == UserRole.VETERINARIAN
        assert update_data["avatar_url"] == "https://example.com/avatar.jpg"
        assert update_data["is_active"] is True
    
    def test_banned_user_inactive(self, role_mapping):
        """Test that banned users are marked as inactive."""
        banned_user = ClerkUser(
            id="user_123",
            created_at=1640995200000,
            updated_at=1640995200000,
            banned=True
        )
        
        create_data = ClerkUserTransform.to_user_create_data(banned_user, role_mapping)
        assert create_data["is_active"] is False
    
    def test_locked_user_inactive(self, role_mapping):
        """Test that locked users are marked as inactive."""
        locked_user = ClerkUser(
            id="user_123",
            created_at=1640995200000,
            updated_at=1640995200000,
            locked=True
        )
        
        create_data = ClerkUserTransform.to_user_create_data(locked_user, role_mapping)
        assert create_data["is_active"] is False


class TestClerkUserValidation:
    """Test ClerkUserValidation functionality."""
    
    @pytest.fixture
    def valid_clerk_user(self) -> ClerkUser:
        """Valid ClerkUser for testing."""
        return ClerkUser(
            id="user_123",
            email_addresses=[
                ClerkEmailAddress(id="email_123", email_address="john.doe@example.com")
            ],
            phone_numbers=[
                ClerkPhoneNumber(id="phone_123", phone_number="+1234567890")
            ],
            first_name="John",
            last_name="Doe",
            created_at=1640995200000,
            updated_at=1640995200000
        )
    
    def test_valid_user_data(self, valid_clerk_user):
        """Test validation of valid user data."""
        errors = ClerkUserValidation.validate_user_data(valid_clerk_user)
        assert len(errors) == 0
    
    def test_missing_required_fields(self):
        """Test validation with missing required fields."""
        invalid_user = ClerkUser(
            id="",  # Missing ID
            created_at=1640995200000,
            updated_at=1640995200000
        )
        
        errors = ClerkUserValidation.validate_user_data(invalid_user)
        assert "Clerk user ID is required" in errors
        assert "Primary email address is required" in errors
        assert "First name is required" in errors
        assert "Last name is required" in errors
    
    def test_invalid_email_format(self):
        """Test validation with invalid email format."""
        # Create a user with manually set invalid email to bypass Pydantic validation
        invalid_user = ClerkUser(
            id="user_123",
            email_addresses=[
                ClerkEmailAddress(id="email_123", email_address="test@example.com")
            ],
            first_name="John",
            last_name="Doe",
            created_at=1640995200000,
            updated_at=1640995200000
        )
        
        # Manually set invalid email to test validation logic
        invalid_user.email_addresses[0].email_address = "invalid-email"
        
        errors = ClerkUserValidation.validate_user_data(invalid_user)
        assert "Invalid email format" in errors
    
    def test_invalid_phone_format(self):
        """Test validation with invalid phone format."""
        invalid_user = ClerkUser(
            id="user_123",
            email_addresses=[
                ClerkEmailAddress(id="email_123", email_address="john@example.com")
            ],
            phone_numbers=[
                ClerkPhoneNumber(id="phone_123", phone_number="invalid-phone")
            ],
            first_name="John",
            last_name="Doe",
            created_at=1640995200000,
            updated_at=1640995200000
        )
        
        errors = ClerkUserValidation.validate_user_data(invalid_user)
        assert "Invalid phone number format" in errors
    
    def test_invalid_timestamps(self):
        """Test validation with invalid timestamps."""
        invalid_user = ClerkUser(
            id="user_123",
            email_addresses=[
                ClerkEmailAddress(id="email_123", email_address="john@example.com")
            ],
            first_name="John",
            last_name="Doe",
            created_at=0,  # Invalid timestamp
            updated_at=-1,  # Invalid timestamp
            last_sign_in_at=0  # Invalid timestamp
        )
        
        errors = ClerkUserValidation.validate_user_data(invalid_user)
        assert "Invalid created_at timestamp" in errors
        assert "Invalid updated_at timestamp" in errors
        assert "Invalid last_sign_in_at timestamp" in errors
    
    def test_valid_role_metadata(self):
        """Test validation of valid role metadata."""
        metadata = {"role": "veterinarian"}
        errors = ClerkUserValidation.validate_role_metadata(metadata)
        assert len(errors) == 0
    
    def test_invalid_role_metadata(self):
        """Test validation of invalid role metadata."""
        metadata = {"role": "invalid_role"}
        errors = ClerkUserValidation.validate_role_metadata(metadata)
        assert len(errors) == 1
        assert "Invalid role 'invalid_role'" in errors[0]
    
    def test_case_insensitive_role_validation(self):
        """Test that role validation is case insensitive."""
        metadata = {"role": "VETERINARIAN"}
        errors = ClerkUserValidation.validate_role_metadata(metadata)
        assert len(errors) == 0  # Should be valid because validation is case insensitive
        
        metadata = {"role": "veterinarian"}
        errors = ClerkUserValidation.validate_role_metadata(metadata)
        assert len(errors) == 0
        
        metadata = {"role": "VeTeRiNaRiAn"}
        errors = ClerkUserValidation.validate_role_metadata(metadata)
        assert len(errors) == 0


class TestClerkWebhookEvent:
    """Test ClerkWebhookEvent schema."""
    
    def test_valid_webhook_event(self):
        """Test valid webhook event creation."""
        event_data = {
            "type": "user.created",
            "object": "event",
            "data": {"id": "user_123", "email": "test@example.com"},
            "timestamp": 1640995200000
        }
        
        event = ClerkWebhookEvent(**event_data)
        assert event.type == "user.created"
        assert event.object == "event"
        assert event.data["id"] == "user_123"
        assert event.timestamp == 1640995200000
        
        expected_datetime = datetime(2022, 1, 1, 0, 0, 0)
        assert event.timestamp_datetime.replace(microsecond=0) == expected_datetime


class TestClerkUserSyncSchemas:
    """Test user synchronization schemas."""
    
    def test_sync_request(self):
        """Test user sync request schema."""
        clerk_user = ClerkUser(
            id="user_123",
            created_at=1640995200000,
            updated_at=1640995200000
        )
        
        request = ClerkUserSyncRequest(
            clerk_user=clerk_user,
            force_update=True,
            sync_metadata=False
        )
        
        assert request.clerk_user.id == "user_123"
        assert request.force_update is True
        assert request.sync_metadata is False
    
    def test_sync_response(self):
        """Test user sync response schema."""
        response = ClerkUserSyncResponse(
            success=True,
            user_id="local_user_123",
            action="created",
            message="User created successfully",
            errors=[]
        )
        
        assert response.success is True
        assert response.user_id == "local_user_123"
        assert response.action == "created"
        assert response.message == "User created successfully"
        assert len(response.errors) == 0


class TestClerkTokenValidationSchemas:
    """Test token validation schemas."""
    
    def test_token_validation_request(self):
        """Test token validation request schema."""
        request = ClerkTokenValidationRequest(
            token="jwt.token.here",
            verify_signature=False
        )
        
        assert request.token == "jwt.token.here"
        assert request.verify_signature is False
    
    def test_token_validation_response(self):
        """Test token validation response schema."""
        response = ClerkTokenValidationResponse(
            valid=True,
            user_id="user_123",
            error=None,
            expires_at=datetime.now()
        )
        
        assert response.valid is True
        assert response.user_id == "user_123"
        assert response.error is None
        assert response.expires_at is not None