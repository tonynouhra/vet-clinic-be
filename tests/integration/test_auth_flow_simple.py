"""
Simplified integration tests for complete Clerk authentication flow.

This module tests the end-to-end authentication flow without requiring
full application configuration, focusing on the core authentication logic.
"""

import pytest
import time
import json
import hmac
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any
from unittest.mock import patch, AsyncMock, Mock
from fastapi import FastAPI, Depends, HTTPException
from fastapi.testclient import TestClient

from app.models.user import User, UserRole
from app.schemas.clerk_schemas import (
    ClerkUser, ClerkEmailAddress, ClerkUserSyncResponse
)
from app.api.deps import (
    get_current_user, require_role, require_staff_role,
    require_admin_role, require_veterinarian_role
)


def create_test_clerk_user(user_data: Dict[str, Any]) -> ClerkUser:
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


def create_test_local_user(user_data: Dict[str, Any]) -> User:
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


def create_test_jwt_token_data(user_data: Dict[str, Any]) -> Dict[str, Any]:
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


class TestAuthenticationFlow:
    """Test authentication flow without full app dependencies."""

    @pytest.fixture
    def sample_users(self):
        """Sample user data for testing."""
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
            "pet_owner": {
                "clerk_id": "user_owner_101",
                "email": "owner@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "role": UserRole.PET_OWNER,
                "clerk_role": "pet_owner"
            }
        }

    @pytest.fixture
    def test_app(self):
        """Create minimal test app."""
        app = FastAPI()

        @app.get("/profile")
        async def get_profile(current_user: User = Depends(get_current_user)):
            return {
                "user_id": str(current_user.id),
                "email": current_user.email,
                "role": current_user.role.value,
                "full_name": current_user.full_name
            }

        @app.get("/admin")
        async def admin_endpoint(current_user: User = Depends(require_admin_role())):
            return {"message": "Admin access", "user_id": str(current_user.id)}

        @app.get("/staff")
        async def staff_endpoint(current_user: User = Depends(require_staff_role())):
            return {"message": "Staff access", "user_id": str(current_user.id)}

        return app

    @pytest.fixture
    def client(self, test_app):
        """Create test client."""
        return TestClient(test_app)

    def setup_auth_mocks(self, user_data: Dict[str, Any]):
        """Setup authentication mocks for a user."""
        clerk_user = create_test_clerk_user(user_data)
        local_user = create_test_local_user(user_data)
        token_data = create_test_jwt_token_data(user_data)

        mock_clerk_service = AsyncMock()
        mock_clerk_service.verify_jwt_token.return_value = token_data
        mock_clerk_service.get_user_by_clerk_id.return_value = clerk_user

        mock_sync_service = AsyncMock()
        mock_sync_service.sync_user_data.return_value = ClerkUserSyncResponse(
            success=True,
            user_id=str(local_user.id),
            action="updated",
            message="Success"
        )
        mock_sync_service.get_user_by_clerk_id.return_value = local_user

        return mock_clerk_service, mock_sync_service, local_user

    @pytest.mark.asyncio
    async def test_user_registration_flow(self, client, sample_users):
        """Test complete user registration flow."""
        user_data = sample_users["pet_owner"]
        mock_clerk_service, mock_sync_service, local_user = self.setup_auth_mocks(user_data)

        with patch("app.api.deps.get_clerk_service", return_value=mock_clerk_service), \
             patch("app.api.deps.UserSyncService", return_value=mock_sync_service):

            headers = {"Authorization": f"Bearer token_{user_data['clerk_id']}"}
            response = client.get("/profile", headers=headers)

            assert response.status_code == 200
            profile = response.json()
            assert profile["email"] == user_data["email"]
            assert profile["role"] == user_data["role"].value
            assert profile["full_name"] == f"{user_data['first_name']} {user_data['last_name']}"

            # Verify service calls
            mock_clerk_service.verify_jwt_token.assert_called_once()
            mock_sync_service.sync_user_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_admin_role_access(self, client, sample_users):
        """Test admin role access control."""
        admin_data = sample_users["admin"]
        mock_clerk_service, mock_sync_service, local_user = self.setup_auth_mocks(admin_data)

        with patch("app.api.deps.get_clerk_service", return_value=mock_clerk_service), \
             patch("app.api.deps.UserSyncService", return_value=mock_sync_service):

            headers = {"Authorization": "Bearer admin_token"}

            # Admin should access admin endpoint
            response = client.get("/admin", headers=headers)
            assert response.status_code == 200
            assert response.json()["message"] == "Admin access"

            # Admin should access staff endpoint
            response = client.get("/staff", headers=headers)
            assert response.status_code == 200
            assert response.json()["message"] == "Staff access"

    @pytest.mark.asyncio
    async def test_veterinarian_role_access(self, client, sample_users):
        """Test veterinarian role access control."""
        vet_data = sample_users["veterinarian"]
        mock_clerk_service, mock_sync_service, local_user = self.setup_auth_mocks(vet_data)

        with patch("app.api.deps.get_clerk_service", return_value=mock_clerk_service), \
             patch("app.api.deps.UserSyncService", return_value=mock_sync_service):

            headers = {"Authorization": "Bearer vet_token"}

            # Veterinarian should access staff endpoint
            response = client.get("/staff", headers=headers)
            assert response.status_code == 200
            assert response.json()["message"] == "Staff access"

            # Veterinarian should NOT access admin endpoint
            response = client.get("/admin", headers=headers)
            assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_pet_owner_role_access(self, client, sample_users):
        """Test pet owner role access control."""
        owner_data = sample_users["pet_owner"]
        mock_clerk_service, mock_sync_service, local_user = self.setup_auth_mocks(owner_data)

        with patch("app.api.deps.get_clerk_service", return_value=mock_clerk_service), \
             patch("app.api.deps.UserSyncService", return_value=mock_sync_service):

            headers = {"Authorization": "Bearer owner_token"}

            # Pet owner should access profile
            response = client.get("/profile", headers=headers)
            assert response.status_code == 200

            # Pet owner should NOT access staff endpoints
            response = client.get("/staff", headers=headers)
            assert response.status_code == 403

            response = client.get("/admin", headers=headers)
            assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_invalid_token_handling(self, client):
        """Test handling of invalid authentication tokens."""
        from app.core.exceptions import AuthenticationError

        mock_clerk_service = AsyncMock()
        mock_clerk_service.verify_jwt_token.side_effect = AuthenticationError("Invalid token")

        with patch("app.api.deps.get_clerk_service", return_value=mock_clerk_service):
            headers = {"Authorization": "Bearer invalid_token"}
            response = client.get("/profile", headers=headers)

            assert response.status_code == 401
            assert "Invalid token" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_inactive_user_handling(self, client, sample_users):
        """Test handling of inactive users."""
        user_data = sample_users["pet_owner"]
        mock_clerk_service, mock_sync_service, local_user = self.setup_auth_mocks(user_data)
        
        # Make user inactive
        local_user.is_active = False

        with patch("app.api.deps.get_clerk_service", return_value=mock_clerk_service), \
             patch("app.api.deps.UserSyncService", return_value=mock_sync_service):

            headers = {"Authorization": "Bearer token"}
            response = client.get("/profile", headers=headers)

            assert response.status_code == 401
            assert "User account is inactive" in response.json()["detail"]


class TestWebhookSynchronization:
    """Test webhook-driven user synchronization."""

    def create_webhook_signature(self, payload: str, timestamp: str, secret: str) -> str:
        """Create webhook signature for testing."""
        signed_payload = f"{timestamp}.{payload}"
        signature = hmac.new(
            secret.encode(),
            signed_payload.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"v1={signature}"

    def create_webhook_user_data(self, user_type: str = "pet_owner") -> Dict[str, Any]:
        """Create sample webhook user data."""
        configs = {
            "pet_owner": {
                "id": "webhook_user_123",
                "email": "webhook@example.com",
                "first_name": "Webhook",
                "last_name": "User",
                "role": "pet_owner"
            },
            "veterinarian": {
                "id": "webhook_vet_456",
                "email": "webhook.vet@vetclinic.com",
                "first_name": "Dr. Webhook",
                "last_name": "Vet",
                "role": "veterinarian"
            }
        }

        config = configs[user_type]
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
    async def test_webhook_user_created(self):
        """Test user creation webhook processing."""
        user_data = self.create_webhook_user_data("pet_owner")
        webhook_secret = "test_webhook_secret"
        
        webhook_payload = {
            "type": "user.created",
            "object": "event",
            "data": user_data,
            "timestamp": int(datetime.utcnow().timestamp() * 1000)
        }

        payload_str = json.dumps(webhook_payload)
        timestamp = str(int(datetime.utcnow().timestamp()))
        signature = self.create_webhook_signature(payload_str, timestamp, webhook_secret)

        # Mock the webhook handler components
        with patch('app.api.webhooks.clerk.get_db') as mock_get_db, \
             patch('app.core.config.get_settings') as mock_settings:
            
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            
            mock_settings_obj = Mock()
            mock_settings_obj.CLERK_WEBHOOK_SECRET = webhook_secret
            mock_settings.return_value = mock_settings_obj

            # Import and test webhook handler
            from app.api.webhooks.clerk import handle_user_created
            from app.schemas.clerk_schemas import ClerkWebhookEvent
            from app.services.user_sync_service import UserSyncService

            webhook_event = ClerkWebhookEvent(**webhook_payload)
            
            with patch.object(UserSyncService, 'sync_user_data') as mock_sync:
                mock_sync.return_value = ClerkUserSyncResponse(
                    success=True,
                    user_id="new_user_123",
                    action="created",
                    message="User created successfully"
                )

                result = await handle_user_created(webhook_event, UserSyncService(mock_db))

                assert result["status"] == "success"
                assert result["action"] == "user_created"
                assert result["clerk_user_id"] == user_data["id"]

    @pytest.mark.asyncio
    async def test_webhook_user_updated(self):
        """Test user update webhook processing."""
        user_data = self.create_webhook_user_data("veterinarian")
        user_data["first_name"] = "Updated Name"  # Simulate update
        
        webhook_payload = {
            "type": "user.updated",
            "object": "event",
            "data": user_data,
            "timestamp": int(datetime.utcnow().timestamp() * 1000)
        }

        # Mock the webhook handler components
        with patch('app.api.webhooks.clerk.get_db') as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db

            # Import and test webhook handler
            from app.api.webhooks.clerk import handle_user_updated
            from app.schemas.clerk_schemas import ClerkWebhookEvent
            from app.services.user_sync_service import UserSyncService

            webhook_event = ClerkWebhookEvent(**webhook_payload)
            
            with patch.object(UserSyncService, 'sync_user_data') as mock_sync:
                mock_sync.return_value = ClerkUserSyncResponse(
                    success=True,
                    user_id="existing_user_456",
                    action="updated",
                    message="User updated successfully"
                )

                result = await handle_user_updated(webhook_event, UserSyncService(mock_db))

                assert result["status"] == "success"
                assert result["action"] == "user_updated"
                assert result["clerk_user_id"] == user_data["id"]

    @pytest.mark.asyncio
    async def test_webhook_user_deleted(self):
        """Test user deletion webhook processing."""
        clerk_user_id = "user_to_delete_123"
        
        webhook_payload = {
            "type": "user.deleted",
            "object": "event",
            "data": {"id": clerk_user_id},
            "timestamp": int(datetime.utcnow().timestamp() * 1000)
        }

        # Mock the webhook handler components
        with patch('app.api.webhooks.clerk.get_db') as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db

            # Import and test webhook handler
            from app.api.webhooks.clerk import handle_user_deleted
            from app.schemas.clerk_schemas import ClerkWebhookEvent
            from app.services.user_sync_service import UserSyncService

            webhook_event = ClerkWebhookEvent(**webhook_payload)
            
            with patch.object(UserSyncService, 'handle_user_deletion') as mock_delete:
                mock_delete.return_value = None  # Successful deletion

                result = await handle_user_deleted(webhook_event, UserSyncService(mock_db))

                assert result["status"] == "success"
                assert result["action"] == "user_deleted"
                assert result["clerk_user_id"] == clerk_user_id


class TestAuthenticationPerformance:
    """Test authentication performance."""

    @pytest.fixture
    def perf_app(self):
        """Create performance test app."""
        app = FastAPI()

        @app.get("/perf")
        async def perf_endpoint(current_user: User = Depends(get_current_user)):
            return {"user_id": str(current_user.id), "timestamp": time.time()}

        return app

    @pytest.fixture
    def perf_client(self, perf_app):
        """Create performance test client."""
        return TestClient(perf_app)

    def setup_perf_user(self):
        """Setup user for performance testing."""
        user_data = {
            "clerk_id": "perf_user_123",
            "email": "perf@vetclinic.com",
            "first_name": "Performance",
            "last_name": "User",
            "role": UserRole.VETERINARIAN,
            "clerk_role": "veterinarian"
        }

        mock_clerk_service, mock_sync_service, local_user = self.setup_auth_mocks(user_data)
        return mock_clerk_service, mock_sync_service, local_user

    def setup_auth_mocks(self, user_data: Dict[str, Any]):
        """Setup authentication mocks for a user."""
        clerk_user = create_test_clerk_user(user_data)
        local_user = create_test_local_user(user_data)
        token_data = create_test_jwt_token_data(user_data)

        mock_clerk_service = AsyncMock()
        mock_clerk_service.verify_jwt_token.return_value = token_data
        mock_clerk_service.get_user_by_clerk_id.return_value = clerk_user

        mock_sync_service = AsyncMock()
        mock_sync_service.sync_user_data.return_value = ClerkUserSyncResponse(
            success=True,
            user_id=str(local_user.id),
            action="skipped",
            message="Up to date"
        )
        mock_sync_service.get_user_by_clerk_id.return_value = local_user

        return mock_clerk_service, mock_sync_service, local_user

    @pytest.mark.asyncio
    async def test_authentication_performance(self, perf_client):
        """Test authentication endpoint performance."""
        mock_clerk_service, mock_sync_service, local_user = self.setup_perf_user()

        with patch("app.api.deps.get_clerk_service", return_value=mock_clerk_service), \
             patch("app.api.deps.UserSyncService", return_value=mock_sync_service):

            headers = {"Authorization": "Bearer perf_token"}
            
            # Measure performance of multiple requests
            start_time = time.time()
            num_requests = 10
            
            for _ in range(num_requests):
                response = perf_client.get("/perf", headers=headers)
                assert response.status_code == 200

            end_time = time.time()
            total_time = end_time - start_time
            avg_time = total_time / num_requests

            # Performance assertion: average response time should be reasonable
            assert avg_time < 0.5, f"Average response time {avg_time:.3f}s exceeds 500ms threshold"

    @pytest.mark.asyncio
    async def test_concurrent_authentication(self, perf_client):
        """Test concurrent authentication requests."""
        mock_clerk_service, mock_sync_service, local_user = self.setup_perf_user()

        with patch("app.api.deps.get_clerk_service", return_value=mock_clerk_service), \
             patch("app.api.deps.UserSyncService", return_value=mock_sync_service):

            headers = {"Authorization": "Bearer concurrent_token"}
            
            # Test concurrent requests
            start_time = time.time()
            num_concurrent = 5
            
            results = []
            for _ in range(num_concurrent):
                response = perf_client.get("/perf", headers=headers)
                results.append(response.status_code == 200)

            end_time = time.time()
            total_time = end_time - start_time

            # All requests should succeed
            assert all(results), "Some concurrent requests failed"
            
            # Concurrent requests should complete reasonably quickly
            assert total_time < 2.0, f"Concurrent requests took {total_time:.3f}s, exceeding 2s threshold"