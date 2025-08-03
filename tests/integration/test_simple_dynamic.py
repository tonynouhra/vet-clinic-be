"""
Simple dynamic test to verify the framework works.
"""

import pytest
import uuid
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch

from app.models.user import User
from app.models.pet import Pet, PetGender, PetSize
from tests.dynamic.decorators import version_parametrize


class TestSimpleDynamic:
    """Simple dynamic test class."""

    @pytest.fixture
    def http_client(self):
        """HTTP client fixture."""
        from app.main import app
        return AsyncClient(app=app, base_url="http://testserver")

    @pytest.fixture
    def mock_user(self):
        """Mock user for authentication."""
        return User(
            id=uuid.uuid4(),
            clerk_id="vet_clerk_123",
            email="vet@example.com",
            first_name="Dr. Jane",
            last_name="Smith",
            is_active=True,
            is_verified=True
        )

    @pytest.mark.asyncio
    async def test_simple_create_pet_v1(self, http_client: AsyncClient, mock_user):
        """Simple test to verify framework works."""
        api_version = "v1"
        
        # Simple test data
        pet_data = {
            "name": "Buddy",
            "species": "dog",
            "owner_id": str(uuid.uuid4())
        }
        
        # Mock pet object
        mock_pet = Pet(
            id=uuid.uuid4(),
            owner_id=uuid.UUID(pet_data["owner_id"]),
            name=pet_data["name"],
            species=pet_data["species"],
            breed="Golden Retriever",
            mixed_breed=False,
            gender=PetGender.MALE,
            size=PetSize.LARGE,
            weight=65.5,
            color="golden",
            is_active=True,
            is_deceased=False
        )
        
        # Build endpoint URL based on version
        endpoint_url = f"/api/{api_version}/pets/"
        
        with patch("app.pets.controller.PetController.create_pet", new_callable=AsyncMock) as mock_create_pet, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user), \
             patch("app.app_helpers.auth_helpers.require_role", return_value=mock_user):
            
            mock_create_pet.return_value = mock_pet
            
            response = await http_client.post(endpoint_url, json=pet_data)
            
            # Debug: Print response details
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text}")
            
            # Basic assertions
            assert response.status_code == 201
            data = response.json()
            assert data["success"] is True
            assert data["version"] == api_version
            assert "data" in data
            
            # Verify controller was called
            mock_create_pet.assert_called_once()
            
            print(f"✓ Test passed for {api_version}")