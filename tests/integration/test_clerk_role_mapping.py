"""
Integration tests for Clerk role mapping with application configuration.
"""
import pytest
from app.schemas.clerk_schemas import ClerkRoleMapping, ClerkUser, ClerkUserTransform, ClerkEmailAddress
from app.models.user import UserRole


class TestClerkRoleMappingIntegration:
    """Test Clerk role mapping integration with the application."""
    
    def test_role_mapping_with_real_config(self):
        """Test role mapping with realistic configuration."""
        role_mapping = ClerkRoleMapping()
        
        # Test all expected role mappings
        test_cases = [
            ("admin", UserRole.ADMIN),
            ("veterinarian", UserRole.VETERINARIAN),
            ("receptionist", UserRole.RECEPTIONIST),
            ("clinic_manager", UserRole.CLINIC_MANAGER),
            ("pet_owner", UserRole.PET_OWNER),
            ("staff", UserRole.RECEPTIONIST),  # Default staff mapping
        ]
        
        for clerk_role, expected_internal_role in test_cases:
            internal_role = role_mapping.get_internal_role(clerk_role)
            assert internal_role == expected_internal_role, f"Role mapping failed for {clerk_role}"
    
    def test_end_to_end_user_transformation(self):
        """Test complete user transformation from Clerk to internal format."""
        # Create a sample Clerk user with veterinarian role
        clerk_user = ClerkUser(
            id="user_vet_123",
            email_addresses=[
                ClerkEmailAddress(id="email_123", email_address="dr.smith@vetclinic.com")
            ],
            first_name="Dr. Sarah",
            last_name="Smith",
            public_metadata={"role": "veterinarian"},
            private_metadata={
                "preferences": {"notifications": True},
                "timezone": "America/New_York"
            },
            created_at=1640995200000,
            updated_at=1640995200000
        )
        
        role_mapping = ClerkRoleMapping()
        user_data = ClerkUserTransform.to_user_create_data(clerk_user, role_mapping)
        
        # Verify the transformation
        assert user_data["clerk_id"] == "user_vet_123"
        assert user_data["email"] == "dr.smith@vetclinic.com"
        assert user_data["first_name"] == "Dr. Sarah"
        assert user_data["last_name"] == "Smith"
        assert user_data["role"] == UserRole.VETERINARIAN
        assert user_data["preferences"] == {"notifications": True}
        assert user_data["timezone"] == "America/New_York"
        assert user_data["is_active"] is True
        assert user_data["is_verified"] is True
    
    def test_pet_owner_default_role(self):
        """Test that users without explicit roles get pet_owner by default."""
        clerk_user = ClerkUser(
            id="user_owner_123",
            email_addresses=[
                ClerkEmailAddress(id="email_123", email_address="john.doe@email.com")
            ],
            first_name="John",
            last_name="Doe",
            public_metadata={},  # No role specified
            created_at=1640995200000,
            updated_at=1640995200000
        )
        
        role_mapping = ClerkRoleMapping()
        user_data = ClerkUserTransform.to_user_create_data(clerk_user, role_mapping)
        
        assert user_data["role"] == UserRole.PET_OWNER
    
    def test_staff_role_mapping_to_receptionist(self):
        """Test that 'staff' role maps to receptionist."""
        clerk_user = ClerkUser(
            id="user_staff_123",
            email_addresses=[
                ClerkEmailAddress(id="email_123", email_address="staff@vetclinic.com")
            ],
            first_name="Jane",
            last_name="Staff",
            public_metadata={"role": "staff"},
            created_at=1640995200000,
            updated_at=1640995200000
        )
        
        role_mapping = ClerkRoleMapping()
        user_data = ClerkUserTransform.to_user_create_data(clerk_user, role_mapping)
        
        assert user_data["role"] == UserRole.RECEPTIONIST
    
    def test_case_insensitive_role_mapping(self):
        """Test that role mapping works with different cases."""
        test_cases = [
            "ADMIN",
            "Admin", 
            "admin",
            "VETERINARIAN",
            "Veterinarian",
            "veterinarian"
        ]
        
        role_mapping = ClerkRoleMapping()
        
        for role_variant in test_cases:
            expected_role = UserRole.ADMIN if "admin" in role_variant.lower() else UserRole.VETERINARIAN
            internal_role = role_mapping.get_internal_role(role_variant)
            assert internal_role == expected_role, f"Case insensitive mapping failed for {role_variant}"
    
    def test_unknown_role_fallback(self):
        """Test that unknown roles fall back to default."""
        unknown_roles = ["unknown", "invalid", "custom_role", None, ""]
        
        role_mapping = ClerkRoleMapping()
        
        for unknown_role in unknown_roles:
            internal_role = role_mapping.get_internal_role(unknown_role)
            assert internal_role == UserRole.PET_OWNER, f"Fallback failed for role: {unknown_role}"
    
    def test_user_update_transformation(self):
        """Test user update transformation preserves existing data structure."""
        clerk_user = ClerkUser(
            id="user_update_123",
            email_addresses=[
                ClerkEmailAddress(id="email_123", email_address="updated@vetclinic.com")
            ],
            first_name="Updated",
            last_name="User",
            public_metadata={"role": "clinic_manager"},
            private_metadata={
                "preferences": {"theme": "dark"},
                "notifications": {"email": False}
            },
            created_at=1640995200000,
            updated_at=1640995200000
        )
        
        role_mapping = ClerkRoleMapping()
        update_data = ClerkUserTransform.to_user_update_data(clerk_user, role_mapping)
        
        # Verify update data structure
        assert "clerk_id" not in update_data  # Should not be in update data
        assert update_data["email"] == "updated@vetclinic.com"
        assert update_data["first_name"] == "Updated"
        assert update_data["last_name"] == "User"
        assert update_data["role"] == UserRole.CLINIC_MANAGER
        assert update_data["preferences"] == {"theme": "dark"}
        assert update_data["notification_settings"] == {"email": False}
        assert update_data["is_active"] is True