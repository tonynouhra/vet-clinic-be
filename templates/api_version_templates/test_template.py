# Template for creating tests for new API versions
# Replace {VERSION}, {RESOURCE}, and placeholders with actual values

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.v{VERSION}.{resource} import {Resource}CreateV{VERSION}, {Resource}ResponseV{VERSION}
from app.models import {Resource}


class Test{Resource}V{VERSION}:
    """Integration tests for V{VERSION} {resource} endpoints."""

    async def test_create_{resource}_v{VERSION}_with_new_fields(self, client: AsyncClient):
        """Test V{VERSION} {resource} creation with new fields."""
        {resource}_data = {
            # Core fields
            "name": "Test {Resource}",
            
            # Fields from previous versions
            # Add fields from previous versions here
            
            # New fields for V{VERSION}
            # "new_field": "new_value",  # New in V{VERSION}
        }
        
        response = await client.post("/api/v{VERSION}/{resource}/", json={resource}_data)
        assert response.status_code == 201
        
        data = response.json()["data"]
        assert data["name"] == "Test {Resource}"
        
        # Verify new V{VERSION} fields are present
        # assert data["new_field"] == "new_value"

    async def test_list_{resource}_v{VERSION}_with_new_filters(self, client: AsyncClient):
        """Test V{VERSION} {resource} listing with new filtering options."""
        # Create test data first
        {resource}_data = {
            "name": "Filterable {Resource}",
            # Add other required fields
        }
        await client.post("/api/v{VERSION}/{resource}/", json={resource}_data)
        
        # Test new V{VERSION} filter parameters
        response = await client.get("/api/v{VERSION}/{resource}/?new_filter=value")
        assert response.status_code == 200
        
        # Verify V{VERSION} response format includes new fields
        {resource}_list = response.json()["data"]
        for {resource} in {resource}_list:
            # Verify new fields are present in response
            # assert "new_field" in {resource}
            pass

    async def test_update_{resource}_v{VERSION}_with_enhanced_fields(self, client: AsyncClient):
        """Test V{VERSION} {resource} update with enhanced fields."""
        # Create {resource} first
        create_data = {
            "name": "Update Test {Resource}",
            # Add required fields
        }
        create_response = await client.post("/api/v{VERSION}/{resource}/", json=create_data)
        {resource}_id = create_response.json()["data"]["id"]
        
        # Update with V{VERSION} fields
        update_data = {
            "name": "Updated {Resource}",
            # "new_field": "updated_value",  # New in V{VERSION}
        }
        
        response = await client.put(f"/api/v{VERSION}/{resource}/{{{resource}_id}}", json=update_data)
        assert response.status_code == 200
        
        data = response.json()["data"]
        assert data["name"] == "Updated {Resource}"
        # assert data["new_field"] == "updated_value"

    async def test_get_{resource}_v{VERSION}_enhanced_response(self, client: AsyncClient):
        """Test V{VERSION} {resource} retrieval with enhanced response format."""
        # Create {resource} first
        create_data = {
            "name": "Enhanced Response {Resource}",
            # Add required fields
        }
        create_response = await client.post("/api/v{VERSION}/{resource}/", json=create_data)
        {resource}_id = create_response.json()["data"]["id"]
        
        # Get {resource} with V{VERSION} endpoint
        response = await client.get(f"/api/v{VERSION}/{resource}/{{{resource}_id}}")
        assert response.status_code == 200
        
        data = response.json()["data"]
        assert data["name"] == "Enhanced Response {Resource}"
        
        # Verify V{VERSION} specific fields are present
        # assert "new_field" in data
        # assert "enhanced_field" in data

    async def test_v{VERSION}_specific_endpoint(self, client: AsyncClient):
        """Test endpoint specific to V{VERSION}."""
        # Create {resource} first
        create_data = {
            "name": "V{VERSION} Specific Test",
            # Add required fields
        }
        create_response = await client.post("/api/v{VERSION}/{resource}/", json=create_data)
        {resource}_id = create_response.json()["data"]["id"]
        
        # Test V{VERSION} specific endpoint
        response = await client.get(f"/api/v{VERSION}/{resource}/{{{resource}_id}}/enhanced-info")
        assert response.status_code == 200
        
        # Verify V{VERSION} specific functionality
        data = response.json()["data"]
        # Add assertions for V{VERSION} specific features
        assert data is not None

    async def test_backward_compatibility_with_previous_versions(self, client: AsyncClient, db: AsyncSession):
        """Test that V{VERSION} doesn't break compatibility with previous versions."""
        # Create {resource} using V{VERSION}
        v{VERSION}_data = {
            "name": "Compatibility Test",
            # Add V{VERSION} specific fields
        }
        v{VERSION}_response = await client.post("/api/v{VERSION}/{resource}/", json=v{VERSION}_data)
        {resource}_id = v{VERSION}_response.json()["data"]["id"]
        
        # Verify previous version endpoints still work
        # Test V{PREVIOUS_VERSION} endpoint (if exists)
        # v{PREVIOUS_VERSION}_response = await client.get(f"/api/v{PREVIOUS_VERSION}/{resource}/{{{resource}_id}}")
        # assert v{PREVIOUS_VERSION}_response.status_code == 200
        
        # Verify data consistency across versions
        # v{PREVIOUS_VERSION}_data = v{PREVIOUS_VERSION}_response.json()["data"]
        # assert v{PREVIOUS_VERSION}_data["name"] == "Compatibility Test"

    async def test_validation_errors_v{VERSION}(self, client: AsyncClient):
        """Test V{VERSION} validation errors."""
        # Test missing required fields
        invalid_data = {
            # Missing required fields
        }
        
        response = await client.post("/api/v{VERSION}/{resource}/", json=invalid_data)
        assert response.status_code == 422
        
        # Test invalid field values
        invalid_data = {
            "name": "",  # Invalid empty name
            # Add other invalid field examples
        }
        
        response = await client.post("/api/v{VERSION}/{resource}/", json=invalid_data)
        assert response.status_code == 422

    async def test_pagination_v{VERSION}(self, client: AsyncClient):
        """Test V{VERSION} pagination functionality."""
        # Create multiple {resource} items
        for i in range(5):
            {resource}_data = {
                "name": f"Pagination Test {Resource} {i}",
                # Add required fields
            }
            await client.post("/api/v{VERSION}/{resource}/", json={resource}_data)
        
        # Test pagination
        response = await client.get("/api/v{VERSION}/{resource}/?page=1&size=2")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["data"]) == 2
        assert data["total"] >= 5
        assert data["page"] == 1
        assert data["size"] == 2


class Test{Resource}V{VERSION}BusinessLogic:
    """Unit tests for V{VERSION} {resource} business logic."""

    async def test_controller_handles_v{VERSION}_schema(self, db: AsyncSession):
        """Test that controller properly handles V{VERSION} schema."""
        from app.{resource}.controller import {Resource}Controller
        
        controller = {Resource}Controller(db)
        
        # Test with V{VERSION} schema
        v{VERSION}_data = {Resource}CreateV{VERSION}(
            name="Controller Test",
            # Add V{VERSION} specific fields
        )
        
        {resource} = await controller.create_{resource}(v{VERSION}_data)
        assert {resource}.name == "Controller Test"
        
        # Verify V{VERSION} specific fields are handled
        # assert {resource}.new_field == v{VERSION}_data.new_field

    async def test_service_layer_v{VERSION}_compatibility(self, db: AsyncSession):
        """Test that service layer handles V{VERSION} parameters."""
        from app.{resource}.services import {Resource}Service
        
        service = {Resource}Service(db)
        
        # Test service with V{VERSION} parameters
        {resource} = await service.create_{resource}(
            name="Service Test",
            # Add V{VERSION} specific parameters
            # new_field="new_value",
        )
        
        assert {resource}.name == "Service Test"
        # assert {resource}.new_field == "new_value"


class Test{Resource}V{VERSION}CrossVersionCompatibility:
    """Tests for cross-version compatibility."""

    async def test_same_controller_works_with_all_versions(self, db: AsyncSession):
        """Test that the same controller works with V1, V2, and V{VERSION} schemas."""
        from app.{resource}.controller import {Resource}Controller
        from app.api.schemas.v1.{resource} import {Resource}CreateV1
        # from app.api.schemas.v2.{resource} import {Resource}CreateV2  # If V2 exists
        
        controller = {Resource}Controller(db)
        
        # Test with V1 schema
        v1_data = {Resource}CreateV1(name="V1 Test")
        {resource}_v1 = await controller.create_{resource}(v1_data)
        assert {resource}_v1.name == "V1 Test"
        
        # Test with V{VERSION} schema (same controller!)
        v{VERSION}_data = {Resource}CreateV{VERSION}(
            name="V{VERSION} Test",
            # Add V{VERSION} specific fields
        )
        {resource}_v{VERSION} = await controller.create_{resource}(v{VERSION}_data)
        assert {resource}_v{VERSION}.name == "V{VERSION} Test"

    async def test_business_logic_consistency_across_versions(self, db: AsyncSession):
        """Test that business rules apply consistently across all API versions."""
        from app.{resource}.controller import {Resource}Controller
        
        controller = {Resource}Controller(db)
        
        # Test business rule with V1
        v1_data = {Resource}CreateV1(name="Duplicate Test")
        await controller.create_{resource}(v1_data)
        
        # Should fail with V{VERSION} schema (same business rule)
        v{VERSION}_data = {Resource}CreateV{VERSION}(name="Duplicate Test")
        with pytest.raises(Exception):  # Replace with specific exception
            await controller.create_{resource}(v{VERSION}_data)