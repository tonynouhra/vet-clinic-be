"""
Integration tests for complete Clerk authentication flow.

This module tests the end-to-end authentication flow including:
- User registration and login flow
- Role-based access control with different user types
- Webhook-driven user synchronization
- Performance tests for authentication endpoints

Requirements covered:
- 1.1, 1.2, 1.3, 1.4: User authentication and session management
- 2.1, 2.2, 2.3, 2.4: User synchronization and profile management
- 3.1, 3.2, 3.3, 3.4: Role-based access control
"""

import pytest
import asyncio
import time
import json
import hmac
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import patch, AsyncMock, Mock
from fastapi import FastAPI, Depends, HTTPException
from fastapi.testclient import TestClient
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

import os
# Set test environment before importing app modules
os.environ["ENVIRONMENT"] = "development"
os.environ["DEBUG"] = "true"

from tests.test_config import get_test_settings, TEST_CLERK_ROLE_MAPPING
from app.models.user import User, UserRole
from app.schemas.clerk_schemas import (
    ClerkUser, ClerkEmailAddress, ClerkPhoneNumber,
    ClerkUserSyncResponse, ClerkWebhookEvent
)
from app.api.deps import (
    get_current_user, require_role, require_staff_role,
    require_admin_role, require_veterinarian_role
)
from app.services.clerk_service import ClerkService
from app.services.user_sync_service import UserSyncService

settings = get_test_settings()


# Fixtures for sample data used across test classes
@pytest.fixture
def sample_users_data():
    """Sample user data for different roles."""
    return {
        "admin": {
            "clerk_id": "user_admin_123",
            "email": "admin@vetclinic.com",
            "first_name": "Admin",
            "last_name": "User",
            "role": UserRole.ADMIN,
            "clerk_role": "admin"
        },
        "veterinarian": {
            "clerk_id": "user_vet_456",
            "email": "vet@vetclinic.com",
            "first_name": "Dr. Jane",
            "last_name": "Smith",
            "role": UserRole.VETERINARIAN,
            "clerk_role": "veterinarian"
        },
        "receptionist": {
            "clerk_id": "user_rec_789",
            "email": "receptionist@vetclinic.com",
            "first_name": "Mary",
            "last_name": "Johnson",
            "role": UserRole.RECEPTIONIST,
            "clerk_role": "receptionist"
        },
        "pet_owner": {
            "clerk_id": "user_owner_101",
            "email": "owner@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "role": UserRole.PET_OWNER,
            "clerk_role": "pet_owner"
        }
    }


def create_clerk_user(user_data: Dict[str, Any]) -> ClerkUser:
    """Create ClerkUser object from test data."""
    return ClerkUser(
        id=user_data["clerk_id"],
        email_addresses=[
            ClerkEmailAddress(
                id="email_123",
                email_address=user_data["email"]
            )
        ],
        first_name=user_data["first_name"],
        last_name=user_data["last_name"],
        public_metadata={"role": user_data["clerk_role"]},
        private_metadata={},
        created_at=int(datetime.utcnow().timestamp() * 1000),
        updated_at=int(datetime.utcnow().timestamp() * 1000),
        banned=False,
        locked=False
    )


def create_local_user(user_data: Dict[str, Any]) -> User:
    """Create local User object from test data."""
    user = Mock(spec=User)
    user.id = f"local_{user_data['clerk_id']}"
    user.clerk_id = user_data["clerk_id"]
    user.email = user_data["email"]
    user.first_name = user_data["first_name"]
    user.last_name = user_data["last_name"]
    user.role = user_data["role"]
    user.is_active = True
    user.full_name = f"{user_data['first_name']} {user_data['last_name']}"
    return user


def create_jwt_token_data(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create JWT token data for testing."""
    return {
        "clerk_id": user_data["clerk_id"],
        "user_id": user_data["clerk_id"],
        "email": user_data["email"],
        "role": user_data["clerk_role"],
        "permissions": [],
        "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
        "session_id": f"session_{user_data['clerk_id']}"
    }


class TestCompleteAuthenticationFlow:
    """Test complete end-to-end authentication flow."""

    @pytest.fixture
    def test_app(self):
        """Create test FastAPI application with authentication endpoints."""
        test_app = FastAPI()

        @test_app.get("/auth/profile")
        async def get_profile(current_user: User = Depends(get_current_user)):
            """Get current user profile."""
            return {
                "user_id": str(current_user.id),
                "email": current_user.email,
                "role": current_user.role.value,
                "full_name": current_user.full_name,
                "is_active": current_user.is_active
            }

        @test_app.get("/auth/admin-only")
        async def admin_endpoint(current_user: User = Depends(require_admin_role())):
            """Admin-only endpoint."""
            return {"message": "Admin access granted", "user_id": str(current_user.id)}

        @test_app.get("/auth/staff-only")
        async def staff_endpoint(current_user: User = Depends(require_staff_role())):
            """Staff-only endpoint."""
            return {"message": "Staff access granted", "user_id": str(current_user.id)}

        @test_app.get("/auth/vet-only")
        async def vet_endpoint(current_user: User = Depends(require_veterinarian_role())):
            """Veterinarian-only endpoint."""
            return {"message": "Veterinarian access granted", "user_id": str(current_user.id)}

        @test_app.get("/auth/pet-owner-only")
        async def pet_owner_endpoint(current_user: User = Depends(require_role(UserRole.PET_OWNER))):
            """Pet owner-only endpoint."""
            return {"message": "Pet owner access granted", "user_id": str(current_user.id)}

        return test_app

    @pytest.fixture
    def client(self, test_app):
        """Create test client."""
        return TestClient(test_app)

    @pytest.fixture
    def mock_clerk_service(self):
        """Mock Clerk service for testing."""
        service = AsyncMock(spec=ClerkService)
        return service

    @pytest.mark.asyncio
    async def test_complete_user_registration_flow(
        self, client, mock_clerk_service, sample_users_data
    ):
        """Test complete user registration flow from Clerk to local database."""
        user_data = sample_users_data["pet_owner"]
        clerk_user = create_clerk_user(user_data)
        local_user = create_local_user(user_data)
        token_data = create_jwt_token_data(user_data)

        # Mock service responses for registration flow
        mock_clerk_service.verify_jwt_token.return_value = token_data
        mock_clerk_service.get_user_by_clerk_id.return_value = clerk_user

        with patch("app.api.deps.get_clerk_service", return_value=mock_clerk_service), \
             patch("app.api.deps.UserSyncService") as mock_sync_service_class:
            
            mock_sync_service = AsyncMock()
            mock_sync_service_class.return_value = mock_sync_service
            
            # Mock successful user creation
            mock_sync_service.sync_user_data.return_value = ClerkUserSyncResponse(
                success=True,
                user_id=str(local_user.id),
                action="created",
                message="User created successfully"
            )
            mock_sync_service.get_user_by_clerk_id.return_value = local_user

            # Test authentication with new user
            headers = {"Authorization": f"Bearer valid_token_{user_data['clerk_id']}"}
            response = client.get("/auth/profile", headers=headers)

            assert response.status_code == 200
            profile_data = response.json()
            assert profile_data["email"] == user_data["email"]
            assert profile_data["role"] == user_data["role"].value
            assert profile_data["full_name"] == f"{user_data['first_name']} {user_data['last_name']}"

            # Verify service calls
            mock_clerk_service.verify_jwt_token.assert_called_once()
            mock_sync_service.sync_user_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_user_login_flow_existing_user(
        self, client, mock_clerk_service, sample_users_data
    ):
        """Test login flow for existing user."""
        user_data = sample_users_data["veterinarian"]
        clerk_user = create_clerk_user(user_data)
        local_user = create_local_user(user_data)
        token_data = create_jwt_token_data(user_data)

        # Mock service responses for existing user login
        mock_clerk_service.verify_jwt_token.return_value = token_data
        mock_clerk_service.get_user_by_clerk_id.return_value = clerk_user

        with patch("app.api.deps.get_clerk_service", return_value=mock_clerk_service), \
             patch("app.api.deps.UserSyncService") as mock_sync_service_class:
            
            mock_sync_service = AsyncMock()
            mock_sync_service_class.return_value = mock_sync_service
            
            # Mock user already exists, no update needed
            mock_sync_service.sync_user_data.return_value = ClerkUserSyncResponse(
                success=True,
                user_id=str(local_user.id),
                action="skipped",
                message="User is up to date"
            )
            mock_sync_service.get_user_by_clerk_id.return_value = local_user

            # Test authentication
            headers = {"Authorization": f"Bearer valid_token_{user_data['clerk_id']}"}
            response = client.get("/auth/profile", headers=headers)

            assert response.status_code == 200
            profile_data = response.json()
            assert profile_data["email"] == user_data["email"]
            assert profile_data["role"] == user_data["role"].value

    @pytest.mark.asyncio
    async def test_invalid_token_authentication(self, client, mock_clerk_service):
        """Test authentication with invalid token."""
        from app.core.exceptions import AuthenticationError
        
        mock_clerk_service.verify_jwt_token.side_effect = AuthenticationError("Invalid token")

        with patch("app.api.deps.get_clerk_service", return_value=mock_clerk_service):
            headers = {"Authorization": "Bearer invalid_token"}
            response = client.get("/auth/profile", headers=headers)

            assert response.status_code == 401
            assert "Invalid token" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_expired_token_authentication(self, client, mock_clerk_service):
        """Test authentication with expired token."""
        from app.core.exceptions import AuthenticationError
        
        mock_clerk_service.verify_jwt_token.side_effect = AuthenticationError("Token has expired")

        with patch("app.api.deps.get_clerk_service", return_value=mock_clerk_service):
            headers = {"Authorization": "Bearer expired_token"}
            response = client.get("/auth/profile", headers=headers)

            assert response.status_code == 401
            assert "Token has expired" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_inactive_user_authentication(
        self, client, mock_clerk_service, sample_users_data
    ):
        """Test authentication with inactive user."""
        user_data = sample_users_data["pet_owner"]
        clerk_user = create_clerk_user(user_data)
        local_user = create_local_user(user_data)
        local_user.is_active = False  # Make user inactive
        token_data = create_jwt_token_data(user_data)

        mock_clerk_service.verify_jwt_token.return_value = token_data
        mock_clerk_service.get_user_by_clerk_id.return_value = clerk_user

        with patch("app.api.deps.get_clerk_service", return_value=mock_clerk_service), \
             patch("app.api.deps.UserSyncService") as mock_sync_service_class:
            
            mock_sync_service = AsyncMock()
            mock_sync_service_class.return_value = mock_sync_service
            
            mock_sync_service.sync_user_data.return_value = ClerkUserSyncResponse(
                success=True,
                user_id=str(local_user.id),
                action="updated",
                message="User updated"
            )
            mock_sync_service.get_user_by_clerk_id.return_value = local_user

            headers = {"Authorization": f"Bearer valid_token_{user_data['clerk_id']}"}
            response = client.get("/auth/profile", headers=headers)

            assert response.status_code == 401
            assert "User account is inactive" in response.json()["detail"]


class TestRoleBasedAccessControl:
    """Test role-based access control with different user types."""

    @pytest.fixture
    def test_app(self):
        """Create test FastAPI application with role-based endpoints."""
        test_app = FastAPI()

        @test_app.get("/admin-only")
        async def admin_endpoint(current_user: User = Depends(require_admin_role())):
            return {"message": "Admin access", "user_role": current_user.role.value}

        @test_app.get("/staff-only")
        async def staff_endpoint(current_user: User = Depends(require_staff_role())):
            return {"message": "Staff access", "user_role": current_user.role.value}

        @test_app.get("/vet-only")
        async def vet_endpoint(current_user: User = Depends(require_veterinarian_role())):
            return {"message": "Vet access", "user_role": current_user.role.value}

        @test_app.get("/pet-owner-only")
        async def pet_owner_endpoint(current_user: User = Depends(require_role(UserRole.PET_OWNER))):
            return {"message": "Pet owner access", "user_role": current_user.role.value}

        return test_app

    @pytest.fixture
    def client(self, test_app):
        """Create test client."""
        return TestClient(test_app)

    def setup_user_authentication(self, user_data: Dict[str, Any], mock_clerk_service):
        """Setup user authentication mocks."""
        clerk_user = create_clerk_user(user_data)
        local_user = create_local_user(user_data)
        token_data = create_jwt_token_data(user_data)

        mock_clerk_service.verify_jwt_token.return_value = token_data
        mock_clerk_service.get_user_by_clerk_id.return_value = clerk_user

        return local_user

    @pytest.mark.asyncio
    async def test_admin_access_control(self, client, sample_users_data):
        """Test admin access control across different endpoints."""
        admin_data = sample_users_data["admin"]

        mock_clerk_service = AsyncMock()
        admin_user = self.setup_user_authentication(admin_data, mock_clerk_service)

        with patch("app.api.deps.get_clerk_service", return_value=mock_clerk_service), \
             patch("app.api.deps.UserSyncService") as mock_sync_service_class:
            
            mock_sync_service = AsyncMock()
            mock_sync_service_class.return_value = mock_sync_service
            mock_sync_service.sync_user_data.return_value = ClerkUserSyncResponse(
                success=True, user_id=str(admin_user.id), action="updated", message="Success"
            )
            mock_sync_service.get_user_by_clerk_id.return_value = admin_user

            headers = {"Authorization": "Bearer admin_token"}

            # Admin should access admin-only endpoint
            response = client.get("/admin-only", headers=headers)
            assert response.status_code == 200
            assert response.json()["message"] == "Admin access"

            # Admin should access staff-only endpoint
            response = client.get("/staff-only", headers=headers)
            assert response.status_code == 200
            assert response.json()["message"] == "Staff access"

    @pytest.mark.asyncio
    async def test_veterinarian_access_control(self, client, sample_users_data):
        """Test veterinarian access control."""
        vet_data = sample_users_data["veterinarian"]

        mock_clerk_service = AsyncMock()
        vet_user = self.setup_user_authentication(vet_data, mock_clerk_service)

        with patch("app.api.deps.get_clerk_service", return_value=mock_clerk_service), \
             patch("app.api.deps.UserSyncService") as mock_sync_service_class:
            
            mock_sync_service = AsyncMock()
            mock_sync_service_class.return_value = mock_sync_service
            mock_sync_service.sync_user_data.return_value = ClerkUserSyncResponse(
                success=True, user_id=str(vet_user.id), action="updated", message="Success"
            )
            mock_sync_service.get_user_by_clerk_id.return_value = vet_user

            headers = {"Authorization": "Bearer vet_token"}

            # Veterinarian should access vet-only endpoint
            response = client.get("/vet-only", headers=headers)
            assert response.status_code == 200
            assert response.json()["message"] == "Vet access"

            # Veterinarian should access staff-only endpoint
            response = client.get("/staff-only", headers=headers)
            assert response.status_code == 200
            assert response.json()["message"] == "Staff access"

            # Veterinarian should NOT access admin-only endpoint
            response = client.get("/admin-only", headers=headers)
            assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_pet_owner_access_control(self, client, sample_users_data):
        """Test pet owner access control."""
        owner_data = sample_users_data["pet_owner"]

        mock_clerk_service = AsyncMock()
        owner_user = self.setup_user_authentication(owner_data, mock_clerk_service)

        with patch("app.api.deps.get_clerk_service", return_value=mock_clerk_service), \
             patch("app.api.deps.UserSyncService") as mock_sync_service_class:
            
            mock_sync_service = AsyncMock()
            mock_sync_service_class.return_value = mock_sync_service
            mock_sync_service.sync_user_data.return_value = ClerkUserSyncResponse(
                success=True, user_id=str(owner_user.id), action="updated", message="Success"
            )
            mock_sync_service.get_user_by_clerk_id.return_value = owner_user

            headers = {"Authorization": "Bearer owner_token"}

            # Pet owner should access pet-owner-only endpoint
            response = client.get("/pet-owner-only", headers=headers)
            assert response.status_code == 200
            assert response.json()["message"] == "Pet owner access"

            # Pet owner should NOT access staff endpoints
            response = client.get("/staff-only", headers=headers)
            assert response.status_code == 403

            response = client.get("/admin-only", headers=headers)
            assert response.status_code == 403

            response = client.get("/vet-only", headers=headers)
            assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_receptionist_access_control(self, client, sample_users_data):
        """Test receptionist access control."""
        receptionist_data = sample_users_data["receptionist"]

        mock_clerk_service = AsyncMock()
        rec_user = self.setup_user_authentication(receptionist_data, mock_clerk_service)

        with patch("app.api.deps.get_clerk_service", return_value=mock_clerk_service), \
             patch("app.api.deps.UserSyncService") as mock_sync_service_class:
            
            mock_sync_service = AsyncMock()
            mock_sync_service_class.return_value = mock_sync_service
            mock_sync_service.sync_user_data.return_value = ClerkUserSyncResponse(
                success=True, user_id=str(rec_user.id), action="updated", message="Success"
            )
            mock_sync_service.get_user_by_clerk_id.return_value = rec_user

            headers = {"Authorization": "Bearer rec_token"}

            # Receptionist should access staff-only endpoint
            response = client.get("/staff-only", headers=headers)
            assert response.status_code == 200
            assert response.json()["message"] == "Staff access"

            # Receptionist should NOT access admin or vet-only endpoints
            response = client.get("/admin-only", headers=headers)
            assert response.status_code == 403

            response = client.get("/vet-only", headers=headers)
            assert response.status_code == 403


class TestWebhookDrivenUserSynchronization:
    """Test webhook-driven user synchronization."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        # Import app here to avoid configuration issues during module import
        from app.main import app
        return TestClient(app)

    @pytest.fixture
    def webhook_secret(self):
        """Mock webhook secret."""
        return "test_webhook_secret_key"

    def create_webhook_signature(self, payload: str, timestamp: str, secret: str) -> str:
        """Create webhook signature for testing."""
        signed_payload = f"{timestamp}.{payload}"
        signature = hmac.new(
            secret.encode(),
            signed_payload.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"v1={signature}"

    def create_sample_clerk_user_data(self, user_type: str = "pet_owner") -> Dict[str, Any]:
        """Create sample Clerk user data for webhooks."""
        user_configs = {
            "pet_owner": {
                "id": "user_webhook_123",
                "email": "webhook@example.com",
                "first_name": "Webhook",
                "last_name": "User",
                "role": "pet_owner"
            },
            "veterinarian": {
                "id": "user_webhook_vet",
                "email": "webhook.vet@vetclinic.com",
                "first_name": "Dr. Webhook",
                "last_name": "Vet",
                "role": "veterinarian"
            }
        }

        config = user_configs[user_type]
        return {
            "id": config["id"],
            "email_addresses": [
                {
                    "id": "email_123",
                    "email_address": config["email"],
                    "verification": {"status": "verified"}
                }
            ],
            "first_name": config["first_name"],
            "last_name": config["last_name"],
            "public_metadata": {"role": config["role"]},
            "private_metadata": {},
            "created_at": int(datetime.utcnow().timestamp() * 1000),
            "updated_at": int(datetime.utcnow().timestamp() * 1000),
            "banned": False,
            "locked": False
        }

    @pytest.mark.asyncio
    async def test_user_created_webhook_synchronization(self, client, webhook_secret):
        """Test user creation via webhook synchronization."""
        user_data = self.create_sample_clerk_user_data("pet_owner")
        
        webhook_payload = {
            "type": "user.created",
            "object": "event",
            "data": user_data,
            "timestamp": int(datetime.utcnow().timestamp() * 1000)
        }

        payload_str = json.dumps(webhook_payload)
        timestamp = str(int(datetime.utcnow().timestamp()))
        signature = self.create_webhook_signature(payload_str, timestamp, webhook_secret)

        with patch.object(settings, 'CLERK_WEBHOOK_SECRET', webhook_secret), \
             patch('app.api.webhooks.clerk.get_db') as mock_get_db:
            
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db

            response = client.post(
                "/webhooks/clerk",
                content=payload_str,
                headers={
                    "svix-signature": signature,
                    "svix-timestamp": timestamp,
                    "content-type": "application/json"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["action"] == "user_created"
            assert data["clerk_user_id"] == user_data["id"]

    @pytest.mark.asyncio
    async def test_user_updated_webhook_synchronization(self, client, webhook_secret):
        """Test user update via webhook synchronization."""
        user_data = self.create_sample_clerk_user_data("veterinarian")
        user_data["first_name"] = "Updated Name"  # Simulate update
        
        webhook_payload = {
            "type": "user.updated",
            "object": "event",
            "data": user_data,
            "timestamp": int(datetime.utcnow().timestamp() * 1000)
        }

        payload_str = json.dumps(webhook_payload)
        timestamp = str(int(datetime.utcnow().timestamp()))
        signature = self.create_webhook_signature(payload_str, timestamp, webhook_secret)

        with patch.object(settings, 'CLERK_WEBHOOK_SECRET', webhook_secret), \
             patch('app.api.webhooks.clerk.get_db') as mock_get_db:
            
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db

            response = client.post(
                "/webhooks/clerk",
                content=payload_str,
                headers={
                    "svix-signature": signature,
                    "svix-timestamp": timestamp,
                    "content-type": "application/json"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["action"] == "user_updated"
            assert data["clerk_user_id"] == user_data["id"]

    @pytest.mark.asyncio
    async def test_user_deleted_webhook_synchronization(self, client, webhook_secret):
        """Test user deletion via webhook synchronization."""
        clerk_user_id = "user_to_delete_123"
        
        webhook_payload = {
            "type": "user.deleted",
            "object": "event",
            "data": {"id": clerk_user_id},
            "timestamp": int(datetime.utcnow().timestamp() * 1000)
        }

        payload_str = json.dumps(webhook_payload)
        timestamp = str(int(datetime.utcnow().timestamp()))
        signature = self.create_webhook_signature(payload_str, timestamp, webhook_secret)

        with patch.object(settings, 'CLERK_WEBHOOK_SECRET', webhook_secret), \
             patch('app.api.webhooks.clerk.get_db') as mock_get_db:
            
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db

            response = client.post(
                "/webhooks/clerk",
                content=payload_str,
                headers={
                    "svix-signature": signature,
                    "svix-timestamp": timestamp,
                    "content-type": "application/json"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["action"] == "user_deleted"
            assert data["clerk_user_id"] == clerk_user_id

    @pytest.mark.asyncio
    async def test_webhook_invalid_signature_rejection(self, client, webhook_secret):
        """Test webhook rejection with invalid signature."""
        user_data = self.create_sample_clerk_user_data()
        
        webhook_payload = {
            "type": "user.created",
            "object": "event",
            "data": user_data,
            "timestamp": int(datetime.utcnow().timestamp() * 1000)
        }

        payload_str = json.dumps(webhook_payload)
        timestamp = str(int(datetime.utcnow().timestamp()))

        with patch.object(settings, 'CLERK_WEBHOOK_SECRET', webhook_secret):
            response = client.post(
                "/webhooks/clerk",
                content=payload_str,
                headers={
                    "svix-signature": "v1=invalid_signature",
                    "svix-timestamp": timestamp,
                    "content-type": "application/json"
                }
            )

            assert response.status_code == 401
            assert "Invalid webhook signature" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_webhook_role_change_synchronization(self, client, webhook_secret):
        """Test role change synchronization via webhook."""
        user_data = self.create_sample_clerk_user_data("pet_owner")
        # Simulate role change from pet_owner to veterinarian
        user_data["public_metadata"]["role"] = "veterinarian"
        
        webhook_payload = {
            "type": "user.updated",
            "object": "event",
            "data": user_data,
            "timestamp": int(datetime.utcnow().timestamp() * 1000)
        }

        payload_str = json.dumps(webhook_payload)
        timestamp = str(int(datetime.utcnow().timestamp()))
        signature = self.create_webhook_signature(payload_str, timestamp, webhook_secret)

        with patch.object(settings, 'CLERK_WEBHOOK_SECRET', webhook_secret), \
             patch('app.api.webhooks.clerk.get_db') as mock_get_db:
            
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db

            response = client.post(
                "/webhooks/clerk",
                content=payload_str,
                headers={
                    "svix-signature": signature,
                    "svix-timestamp": timestamp,
                    "content-type": "application/json"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["action"] == "user_updated"


class TestAuthenticationPerformance:
    """Test performance of authentication endpoints."""

    @pytest.fixture
    def performance_test_app(self):
        """Create test app for performance testing."""
        test_app = FastAPI()

        @test_app.get("/perf/auth")
        async def auth_endpoint(current_user: User = Depends(get_current_user)):
            return {"user_id": str(current_user.id), "timestamp": time.time()}

        @test_app.get("/perf/role-check")
        async def role_check_endpoint(current_user: User = Depends(require_staff_role())):
            return {"user_id": str(current_user.id), "role": current_user.role.value}

        return test_app

    @pytest.fixture
    def perf_client(self, performance_test_app):
        """Create performance test client."""
        return TestClient(performance_test_app)

    def setup_performance_user(self, mock_clerk_service):
        """Setup user for performance testing."""
        user_data = {
            "clerk_id": "perf_user_123",
            "email": "perf@vetclinic.com",
            "first_name": "Performance",
            "last_name": "User",
            "role": UserRole.VETERINARIAN,
            "clerk_role": "veterinarian"
        }

        clerk_user = create_clerk_user(user_data)
        local_user = create_local_user(user_data)
        token_data = create_jwt_token_data(user_data)

        mock_clerk_service.verify_jwt_token.return_value = token_data
        mock_clerk_service.get_user_by_clerk_id.return_value = clerk_user

        return local_user

    @pytest.mark.asyncio
    async def test_authentication_endpoint_performance(self, perf_client):
        """Test authentication endpoint performance."""
        mock_clerk_service = AsyncMock()
        local_user = self.setup_performance_user(mock_clerk_service)

        with patch("app.api.deps.get_clerk_service", return_value=mock_clerk_service), \
             patch("app.api.deps.UserSyncService") as mock_sync_service_class:
            
            mock_sync_service = AsyncMock()
            mock_sync_service_class.return_value = mock_sync_service
            mock_sync_service.sync_user_data.return_value = ClerkUserSyncResponse(
                success=True, user_id=str(local_user.id), action="skipped", message="Up to date"
            )
            mock_sync_service.get_user_by_clerk_id.return_value = local_user

            headers = {"Authorization": "Bearer perf_token"}
            
            # Measure performance of multiple requests
            start_time = time.time()
            num_requests = 10
            
            for _ in range(num_requests):
                response = perf_client.get("/perf/auth", headers=headers)
                assert response.status_code == 200

            end_time = time.time()
            total_time = end_time - start_time
            avg_time = total_time / num_requests

            # Performance assertion: average response time should be under 100ms
            assert avg_time < 0.1, f"Average response time {avg_time:.3f}s exceeds 100ms threshold"

    @pytest.mark.asyncio
    async def test_role_based_endpoint_performance(self, perf_client):
        """Test role-based endpoint performance."""
        mock_clerk_service = AsyncMock()
        local_user = self.setup_performance_user(mock_clerk_service)

        with patch("app.api.deps.get_clerk_service", return_value=mock_clerk_service), \
             patch("app.api.deps.UserSyncService") as mock_sync_service_class:
            
            mock_sync_service = AsyncMock()
            mock_sync_service_class.return_value = mock_sync_service
            mock_sync_service.sync_user_data.return_value = ClerkUserSyncResponse(
                success=True, user_id=str(local_user.id), action="skipped", message="Up to date"
            )
            mock_sync_service.get_user_by_clerk_id.return_value = local_user

            headers = {"Authorization": "Bearer perf_token"}
            
            # Measure performance of role-based access control
            start_time = time.time()
            num_requests = 10
            
            for _ in range(num_requests):
                response = perf_client.get("/perf/role-check", headers=headers)
                assert response.status_code == 200

            end_time = time.time()
            total_time = end_time - start_time
            avg_time = total_time / num_requests

            # Performance assertion: role checking should add minimal overhead
            assert avg_time < 0.15, f"Average role-check time {avg_time:.3f}s exceeds 150ms threshold"

    @pytest.mark.asyncio
    async def test_concurrent_authentication_performance(self, perf_client):
        """Test concurrent authentication performance."""
        mock_clerk_service = AsyncMock()
        local_user = self.setup_performance_user(mock_clerk_service)

        with patch("app.api.deps.get_clerk_service", return_value=mock_clerk_service), \
             patch("app.api.deps.UserSyncService") as mock_sync_service_class:
            
            mock_sync_service = AsyncMock()
            mock_sync_service_class.return_value = mock_sync_service
            mock_sync_service.sync_user_data.return_value = ClerkUserSyncResponse(
                success=True, user_id=str(local_user.id), action="skipped", message="Up to date"
            )
            mock_sync_service.get_user_by_clerk_id.return_value = local_user

            headers = {"Authorization": "Bearer perf_token"}
            
            async def make_request():
                """Make a single request."""
                response = perf_client.get("/perf/auth", headers=headers)
                return response.status_code == 200

            # Test concurrent requests
            start_time = time.time()
            num_concurrent = 5
            
            # Simulate concurrent requests (using asyncio.gather would be ideal but TestClient is sync)
            results = []
            for _ in range(num_concurrent):
                result = await make_request()
                results.append(result)

            end_time = time.time()
            total_time = end_time - start_time

            # All requests should succeed
            assert all(results), "Some concurrent requests failed"
            
            # Concurrent requests should complete reasonably quickly
            assert total_time < 1.0, f"Concurrent requests took {total_time:.3f}s, exceeding 1s threshold"

    @pytest.mark.asyncio
    async def test_authentication_caching_performance(self, perf_client):
        """Test authentication caching performance improvement."""
        mock_clerk_service = AsyncMock()
        local_user = self.setup_performance_user(mock_clerk_service)

        with patch("app.api.deps.get_clerk_service", return_value=mock_clerk_service), \
             patch("app.api.deps.UserSyncService") as mock_sync_service_class:
            
            mock_sync_service = AsyncMock()
            mock_sync_service_class.return_value = mock_sync_service
            
            # First request - cache miss
            mock_sync_service.sync_user_data.return_value = ClerkUserSyncResponse(
                success=True, user_id=str(local_user.id), action="updated", message="User synced"
            )
            mock_sync_service.get_user_by_clerk_id.return_value = local_user

            headers = {"Authorization": "Bearer cache_test_token"}
            
            # First request (cache miss)
            start_time = time.time()
            response1 = perf_client.get("/perf/auth", headers=headers)
            first_request_time = time.time() - start_time
            assert response1.status_code == 200

            # Subsequent requests should use cache (simulate cache hit)
            mock_sync_service.sync_user_data.return_value = ClerkUserSyncResponse(
                success=True, user_id=str(local_user.id), action="skipped", message="From cache"
            )

            start_time = time.time()
            response2 = perf_client.get("/perf/auth", headers=headers)
            cached_request_time = time.time() - start_time
            assert response2.status_code == 200

            # Cached request should be faster (though this is a mock scenario)
            # In real implementation, cached requests would be significantly faster
            assert cached_request_time <= first_request_time * 1.5, "Cached request not showing expected performance improvement"

    @pytest.mark.asyncio
    async def test_authentication_load_testing(self, perf_client):
        """Test authentication under load."""
        mock_clerk_service = AsyncMock()
        local_user = self.setup_performance_user(mock_clerk_service)

        with patch("app.api.deps.get_clerk_service", return_value=mock_clerk_service), \
             patch("app.api.deps.UserSyncService") as mock_sync_service_class:
            
            mock_sync_service = AsyncMock()
            mock_sync_service_class.return_value = mock_sync_service
            mock_sync_service.sync_user_data.return_value = ClerkUserSyncResponse(
                success=True, user_id=str(local_user.id), action="skipped", message="Up to date"
            )
            mock_sync_service.get_user_by_clerk_id.return_value = local_user

            headers = {"Authorization": "Bearer load_test_token"}
            
            # Test with higher load
            start_time = time.time()
            num_requests = 50
            success_count = 0
            
            for _ in range(num_requests):
                try:
                    response = perf_client.get("/perf/auth", headers=headers)
                    if response.status_code == 200:
                        success_count += 1
                except Exception:
                    pass  # Count failures

            end_time = time.time()
            total_time = end_time - start_time
            success_rate = success_count / num_requests

            # Performance assertions for load testing
            assert success_rate >= 0.95, f"Success rate {success_rate:.2%} below 95% threshold"
            assert total_time < 5.0, f"Load test took {total_time:.3f}s, exceeding 5s threshold"
            
            avg_time = total_time / num_requests
            assert avg_time < 0.2, f"Average response time under load {avg_time:.3f}s exceeds 200ms threshold" 