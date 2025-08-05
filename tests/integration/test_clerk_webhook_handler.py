"""
Integration tests for Clerk webhook handler.
Tests webhook event processing for user.created, user.updated, and user.deleted events.
"""

import pytest
import json
import hmac
import hashlib
from datetime import datetime
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.config import get_settings
from app.core.database import Base, get_db
from app.models.user import User, UserRole
from app.schemas.clerk_schemas import ClerkUser


settings = get_settings()


@pytest.fixture
def test_db_session():
    """Create a test database session."""
    # Use in-memory SQLite for testing
    engine = create_engine("sqlite:///:memory:", echo=False)
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        session.close()


class TestClerkWebhookHandler:
    """Test cases for Clerk webhook handler."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def webhook_secret(self):
        """Mock webhook secret."""
        return "test_webhook_secret_key"

    @pytest.fixture
    def sample_clerk_user_data(self):
        """Sample Clerk user data for testing."""
        return {
            "id": "user_test123",
            "email_addresses": [
                {
                    "id": "email_123",
                    "email_address": "test@example.com",
                    "verification": {"status": "verified"},
                    "linked_to": []
                }
            ],
            "phone_numbers": [
                {
                    "id": "phone_123",
                    "phone_number": "+1234567890",
                    "verification": {"status": "verified"},
                    "linked_to": []
                }
            ],
            "first_name": "John",
            "last_name": "Doe",
            "image_url": "https://example.com/avatar.jpg",
            "has_image": True,
            "public_metadata": {"role": "pet_owner"},
            "private_metadata": {
                "preferences": {"theme": "dark"},
                "notifications": {"email": True}
            },
            "unsafe_metadata": {},
            "created_at": int(datetime.utcnow().timestamp() * 1000),
            "updated_at": int(datetime.utcnow().timestamp() * 1000),
            "last_sign_in_at": int(datetime.utcnow().timestamp() * 1000),
            "banned": False,
            "locked": False,
            "lockout_expires_in_seconds": None,
            "verification_attempts_remaining": 3
        }

    def create_webhook_signature(self, payload: str, timestamp: str, secret: str) -> str:
        """Create webhook signature for testing."""
        signed_payload = f"{timestamp}.{payload}"
        signature = hmac.new(
            secret.encode(),
            signed_payload.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"v1={signature}"

    @pytest.mark.asyncio
    async def test_webhook_health_check(self, client):
        """Test webhook health check endpoint."""
        response = client.get("/webhooks/clerk/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "clerk_webhook_handler"
        assert "supported_events" in data

    @pytest.mark.asyncio
    async def test_webhook_missing_signature(self, client, sample_clerk_user_data, webhook_secret):
        """Test webhook request without signature header."""
        webhook_payload = {
            "type": "user.created",
            "object": "event",
            "data": sample_clerk_user_data,
            "timestamp": int(datetime.utcnow().timestamp() * 1000)
        }
        
        with patch.object(settings, 'CLERK_WEBHOOK_SECRET', webhook_secret):
            response = client.post(
                "/webhooks/clerk",
                json=webhook_payload
            )
        
        assert response.status_code == 400
        assert "Missing webhook signature" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_webhook_invalid_signature(self, client, sample_clerk_user_data, webhook_secret):
        """Test webhook request with invalid signature."""
        webhook_payload = {
            "type": "user.created",
            "object": "event",
            "data": sample_clerk_user_data,
            "timestamp": int(datetime.utcnow().timestamp() * 1000)
        }
        
        timestamp = str(int(datetime.utcnow().timestamp()))
        
        with patch.object(settings, 'CLERK_WEBHOOK_SECRET', webhook_secret):
            response = client.post(
                "/webhooks/clerk",
                json=webhook_payload,
                headers={
                    "svix-signature": "v1=invalid_signature",
                    "svix-timestamp": timestamp
                }
            )
        
        assert response.status_code == 401
        assert "Invalid webhook signature" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_user_created_webhook_success(
        self, 
        client, 
        sample_clerk_user_data, 
        webhook_secret,
        test_db_session
    ):
        """Test successful user.created webhook processing."""
        webhook_payload = {
            "type": "user.created",
            "object": "event",
            "data": sample_clerk_user_data,
            "timestamp": int(datetime.utcnow().timestamp() * 1000)
        }
        
        payload_str = json.dumps(webhook_payload)
        timestamp = str(int(datetime.utcnow().timestamp()))
        signature = self.create_webhook_signature(payload_str, timestamp, webhook_secret)
        
        with patch.object(settings, 'CLERK_WEBHOOK_SECRET', webhook_secret):
            with patch('app.api.webhooks.clerk.get_db', return_value=test_db_session):
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
        assert data["clerk_user_id"] == sample_clerk_user_data["id"]

    @pytest.mark.asyncio
    async def test_user_updated_webhook_success(
        self, 
        client, 
        sample_clerk_user_data, 
        webhook_secret,
        test_db_session
    ):
        """Test successful user.updated webhook processing."""
        # First create a user
        user = User(
            clerk_id=sample_clerk_user_data["id"],
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            role=UserRole.PET_OWNER,
            is_active=True,
            is_verified=True
        )
        test_db_session.add(user)
        await test_db_session.commit()
        
        # Update user data
        updated_data = sample_clerk_user_data.copy()
        updated_data["first_name"] = "Jane"
        updated_data["last_name"] = "Smith"
        
        webhook_payload = {
            "type": "user.updated",
            "object": "event",
            "data": updated_data,
            "timestamp": int(datetime.utcnow().timestamp() * 1000)
        }
        
        payload_str = json.dumps(webhook_payload)
        timestamp = str(int(datetime.utcnow().timestamp()))
        signature = self.create_webhook_signature(payload_str, timestamp, webhook_secret)
        
        with patch.object(settings, 'CLERK_WEBHOOK_SECRET', webhook_secret):
            with patch('app.api.webhooks.clerk.get_db', return_value=test_db_session):
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
        assert data["clerk_user_id"] == sample_clerk_user_data["id"]

    @pytest.mark.asyncio
    async def test_user_deleted_webhook_success(
        self, 
        client, 
        sample_clerk_user_data, 
        webhook_secret,
        test_db_session
    ):
        """Test successful user.deleted webhook processing."""
        # First create a user
        user = User(
            clerk_id=sample_clerk_user_data["id"],
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            role=UserRole.PET_OWNER,
            is_active=True,
            is_verified=True
        )
        test_db_session.add(user)
        await test_db_session.commit()
        
        webhook_payload = {
            "type": "user.deleted",
            "object": "event",
            "data": {"id": sample_clerk_user_data["id"]},
            "timestamp": int(datetime.utcnow().timestamp() * 1000)
        }
        
        payload_str = json.dumps(webhook_payload)
        timestamp = str(int(datetime.utcnow().timestamp()))
        signature = self.create_webhook_signature(payload_str, timestamp, webhook_secret)
        
        with patch.object(settings, 'CLERK_WEBHOOK_SECRET', webhook_secret):
            with patch('app.api.webhooks.clerk.get_db', return_value=test_db_session):
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
        assert data["clerk_user_id"] == sample_clerk_user_data["id"]

    @pytest.mark.asyncio
    async def test_unsupported_webhook_event(
        self, 
        client, 
        sample_clerk_user_data, 
        webhook_secret
    ):
        """Test webhook with unsupported event type."""
        webhook_payload = {
            "type": "session.created",
            "object": "event",
            "data": sample_clerk_user_data,
            "timestamp": int(datetime.utcnow().timestamp() * 1000)
        }
        
        payload_str = json.dumps(webhook_payload)
        timestamp = str(int(datetime.utcnow().timestamp()))
        signature = self.create_webhook_signature(payload_str, timestamp, webhook_secret)
        
        with patch.object(settings, 'CLERK_WEBHOOK_SECRET', webhook_secret):
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
        assert data["status"] == "ignored"
        assert "not handled" in data["message"]

    @pytest.mark.asyncio
    async def test_webhook_invalid_payload_structure(
        self, 
        client, 
        webhook_secret
    ):
        """Test webhook with invalid payload structure."""
        webhook_payload = {
            "invalid": "structure",
            "missing": "required_fields"
        }
        
        payload_str = json.dumps(webhook_payload)
        timestamp = str(int(datetime.utcnow().timestamp()))
        signature = self.create_webhook_signature(payload_str, timestamp, webhook_secret)
        
        with patch.object(settings, 'CLERK_WEBHOOK_SECRET', webhook_secret):
            response = client.post(
                "/webhooks/clerk",
                content=payload_str,
                headers={
                    "svix-signature": signature,
                    "svix-timestamp": timestamp,
                    "content-type": "application/json"
                }
            )
        
        assert response.status_code == 400
        assert "Invalid webhook event structure" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_webhook_database_error_handling(
        self, 
        client, 
        sample_clerk_user_data, 
        webhook_secret
    ):
        """Test webhook error handling when database operations fail."""
        webhook_payload = {
            "type": "user.created",
            "object": "event",
            "data": sample_clerk_user_data,
            "timestamp": int(datetime.utcnow().timestamp() * 1000)
        }
        
        payload_str = json.dumps(webhook_payload)
        timestamp = str(int(datetime.utcnow().timestamp()))
        signature = self.create_webhook_signature(payload_str, timestamp, webhook_secret)
        
        # Mock database session to raise an exception
        mock_db = AsyncMock()
        mock_db.add.side_effect = Exception("Database connection failed")
        
        with patch.object(settings, 'CLERK_WEBHOOK_SECRET', webhook_secret):
            with patch('app.api.webhooks.clerk.get_db', return_value=mock_db):
                response = client.post(
                    "/webhooks/clerk",
                    content=payload_str,
                    headers={
                        "svix-signature": signature,
                        "svix-timestamp": timestamp,
                        "content-type": "application/json"
                    }
                )
        
        assert response.status_code == 500
        assert "Webhook processing failed" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_webhook_missing_timestamp_header(
        self, 
        client, 
        sample_clerk_user_data, 
        webhook_secret
    ):
        """Test webhook request without timestamp header."""
        webhook_payload = {
            "type": "user.created",
            "object": "event",
            "data": sample_clerk_user_data,
            "timestamp": int(datetime.utcnow().timestamp() * 1000)
        }
        
        payload_str = json.dumps(webhook_payload)
        
        with patch.object(settings, 'CLERK_WEBHOOK_SECRET', webhook_secret):
            response = client.post(
                "/webhooks/clerk",
                content=payload_str,
                headers={
                    "svix-signature": "v1=some_signature",
                    "content-type": "application/json"
                }
            )
        
        assert response.status_code == 400
        assert "Missing webhook timestamp" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_webhook_no_secret_configured(
        self, 
        client, 
        sample_clerk_user_data
    ):
        """Test webhook when no secret is configured."""
        webhook_payload = {
            "type": "user.created",
            "object": "event",
            "data": sample_clerk_user_data,
            "timestamp": int(datetime.utcnow().timestamp() * 1000)
        }
        
        payload_str = json.dumps(webhook_payload)
        timestamp = str(int(datetime.utcnow().timestamp()))
        
        with patch.object(settings, 'CLERK_WEBHOOK_SECRET', None):
            response = client.post(
                "/webhooks/clerk",
                content=payload_str,
                headers={
                    "svix-signature": "v1=some_signature",
                    "svix-timestamp": timestamp,
                    "content-type": "application/json"
                }
            )
        
        assert response.status_code == 500
        assert "Webhook secret not configured" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_user_created_duplicate_email(
        self, 
        client, 
        sample_clerk_user_data, 
        webhook_secret,
        test_db_session
    ):
        """Test user.created webhook when email already exists."""
        # First create a user with the same email
        existing_user = User(
            clerk_id="different_clerk_id",
            email=sample_clerk_user_data["email_addresses"][0]["email_address"],
            first_name="Existing",
            last_name="User",
            role=UserRole.PET_OWNER,
            is_active=True,
            is_verified=True
        )
        test_db_session.add(existing_user)
        await test_db_session.commit()
        
        webhook_payload = {
            "type": "user.created",
            "object": "event",
            "data": sample_clerk_user_data,
            "timestamp": int(datetime.utcnow().timestamp() * 1000)
        }
        
        payload_str = json.dumps(webhook_payload)
        timestamp = str(int(datetime.utcnow().timestamp()))
        signature = self.create_webhook_signature(payload_str, timestamp, webhook_secret)
        
        with patch.object(settings, 'CLERK_WEBHOOK_SECRET', webhook_secret):
            with patch('app.api.webhooks.clerk.get_db', return_value=test_db_session):
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
        assert data["status"] == "error"
        assert data["action"] == "user_created"
        assert "Email already in use" in data["message"] or "errors" in data

    @pytest.mark.asyncio
    async def test_user_deleted_nonexistent_user(
        self, 
        client, 
        webhook_secret,
        test_db_session
    ):
        """Test user.deleted webhook for non-existent user."""
        webhook_payload = {
            "type": "user.deleted",
            "object": "event",
            "data": {"id": "nonexistent_user_id"},
            "timestamp": int(datetime.utcnow().timestamp() * 1000)
        }
        
        payload_str = json.dumps(webhook_payload)
        timestamp = str(int(datetime.utcnow().timestamp()))
        signature = self.create_webhook_signature(payload_str, timestamp, webhook_secret)
        
        with patch.object(settings, 'CLERK_WEBHOOK_SECRET', webhook_secret):
            with patch('app.api.webhooks.clerk.get_db', return_value=test_db_session):
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
        # Should succeed even if user doesn't exist (idempotent operation)