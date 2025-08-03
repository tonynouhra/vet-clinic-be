# Common Testing Scenarios

This document provides examples of common testing scenarios using the dynamic API testing framework.

## Table of Contents

1. [Basic CRUD Operations](#basic-crud-operations)
2. [Feature-Specific Testing](#feature-specific-testing)
3. [Error Handling and Validation](#error-handling-and-validation)
4. [Data Consistency Across Versions](#data-consistency-across-versions)
5. [Performance and Load Testing](#performance-and-load-testing)
6. [Authentication and Authorization](#authentication-and-authorization)
7. [Complex Workflows](#complex-workflows)
8. [Batch Operations](#batch-operations)
9. [Search and Filtering](#search-and-filtering)
10. [File Upload and Media](#file-upload-and-media)

## Basic CRUD Operations

### Complete CRUD Test Suite

```python
from tests.dynamic.fixtures import parametrize_versions
from tests.dynamic.base_test import BaseVersionTest
import pytest

@parametrize_versions()
class TestPetCRUD:
    """Complete CRUD operations testing across all API versions."""
    
    async def test_create_pet(self, api_version: str, base_test: BaseVersionTest, async_client):
        """Test pet creation with version-appropriate data."""
        # Generate version-specific test data
        pet_data = base_test.build_test_data(
            api_version, "pet", "create",
            name="CRUD Test Pet",
            species="dog",
            breed="labrador"
        )
        
        # Create pet
        endpoint = base_test.get_endpoint_url(api_version, "pets")
        response = await base_test.make_request("POST", endpoint, async_client, json=pet_data)
        
        # Validate creation
        base_test.assert_status_code(response, 201, "Creating pet")
        created_pet = response.json()
        
        # Validate response structure
        base_test.validate_response_structure(created_pet, api_version, "pet")
        
        # Validate data integrity
        assert created_pet["name"] == pet_data["name"]
        assert created_pet["species"] == pet_data["species"]
        assert "id" in created_pet
        
        # Cleanup
        await base_test.cleanup_test_resource(async_client, api_version, "pet", created_pet["id"])
    
    async def test_read_pet(self, api_version: str, base_test: BaseVersionTest, async_client):
        """Test pet retrieval with version-specific response validation."""
        # Create test pet
        pet = await base_test.create_test_resource(
            async_client, api_version, "pet",
            name="Read Test Pet"
        )
        
        try:
            # Read pet
            endpoint = base_test.get_endpoint_url(api_version, "pets", pet["id"])
            response = await base_test.make_request("GET", endpoint, async_client)
            
            # Validate response
            base_test.assert_status_code(response, 200, "Reading pet")
            retrieved_pet = response.json()
            
            # Validate structure and version-specific fields
            base_test.validate_response_structure(retrieved_pet, api_version, "pet")
            base_test.validate_version_specific_fields(retrieved_pet, api_version, "pet")
            
            # Validate data consistency
            assert retrieved_pet["id"] == pet["id"]
            assert retrieved_pet["name"] == pet["name"]
            
        finally:
            await base_test.cleanup_test_resource(async_client, api_version, "pet", pet["id"])
    
    async def test_update_pet(self, api_version: str, base_test: BaseVersionTest, async_client):
        """Test pet updates with version-appropriate fields."""
        # Create test pet
        pet = await base_test.create_test_resource(
            async_client, api_version, "pet",
            name="Update Test Pet"
        )
        
        try:
            # Prepare update data
            update_data = base_test.build_test_data(
                api_version, "pet", "update",
                name="Updated Pet Name",
                breed="golden_retriever"
            )
            
            # Update pet
            endpoint = base_test.get_endpoint_url(api_version, "pets", pet["id"])
            response = await base_test.make_request("PUT", endpoint, async_client, json=update_data)
            
            # Validate update
            base_test.assert_status_code(response, 200, "Updating pet")
            updated_pet = response.json()
            
            # Validate changes
            assert updated_pet["name"] == update_data["name"]
            assert updated_pet["breed"] == update_data["breed"]
            assert updated_pet["id"] == pet["id"]  # ID should not change
            
            # Validate version-specific fields are preserved/updated correctly
            base_test.validate_version_specific_fields(updated_pet, api_version, "pet")
            
        finally:
            await base_test.cleanup_test_resource(async_client, api_version, "pet", pet["id"])
    
    async def test_delete_pet(self, api_version: str, base_test: BaseVersionTest, async_client):
        """Test pet deletion with consistent behavior across versions."""
        # Create test pet
        pet = await base_test.create_test_resource(
            async_client, api_version, "pet",
            name="Delete Test Pet"
        )
        
        # Delete pet
        endpoint = base_test.get_endpoint_url(api_version, "pets", pet["id"])
        response = await base_test.make_request("DELETE", endpoint, async_client)
        
        # Validate deletion (accept both 200 and 204)
        assert response.status_code in [200, 204], f"Expected 200 or 204, got {response.status_code}"
        
        # Verify pet is actually deleted
        get_response = await base_test.make_request("GET", endpoint, async_client)
        base_test.assert_status_code(get_response, 404, "Verifying pet deletion")
    
    async def test_list_pets(self, api_version: str, base_test: BaseVersionTest, async_client):
        """Test pet listing with version-specific response format."""
        # Create multiple test pets
        pets = []
        for i in range(3):
            pet = await base_test.create_test_resource(
                async_client, api_version, "pet",
                name=f"List Test Pet {i+1}"
            )
            pets.append(pet)
        
        try:
            # List pets
            endpoint = base_test.get_endpoint_url(api_version, "pets")
            response = await base_test.make_request("GET", endpoint, async_client)
            
            # Validate response
            base_test.assert_status_code(response, 200, "Listing pets")
            pets_list = response.json()
            
            # Validate list structure
            assert isinstance(pets_list, list) or "items" in pets_list
            
            # Extract items if paginated response
            items = pets_list if isinstance(pets_list, list) else pets_list["items"]
            
            # Validate each pet in the list
            for pet_item in items:
                base_test.validate_response_structure(pet_item, api_version, "pet")
            
            # Verify our test pets are in the list
            pet_ids = {pet["id"] for pet in pets}
            listed_ids = {item["id"] for item in items}
            assert pet_ids.issubset(listed_ids), "Not all created pets found in list"
            
        finally:
            # Cleanup all test pets
            for pet in pets:
                await base_test.cleanup_test_resource(async_client, api_version, "pet", pet["id"])
```

### Resource Relationship Testing

```python
@parametrize_versions()
class TestResourceRelationships:
    """Test relationships between different resources."""
    
    async def test_pet_owner_relationship(self, api_version: str, base_test: BaseVersionTest, async_client):
        """Test pet-owner relationship consistency."""
        # Create test user (owner)
        user = await base_test.create_test_resource(
            async_client, api_version, "user",
            email="owner@example.com",
            first_name="Pet",
            last_name="Owner"
        )
        
        try:
            # Create pet with owner relationship
            pet = await base_test.create_test_resource(
                async_client, api_version, "pet",
                name="Relationship Test Pet",
                owner_id=user["id"]
            )
            
            try:
                # Verify relationship in pet data
                pet_endpoint = base_test.get_endpoint_url(api_version, "pets", pet["id"])
                pet_response = await base_test.make_request("GET", pet_endpoint, async_client)
                pet_data = pet_response.json()
                
                assert pet_data["owner_id"] == user["id"]
                
                # If version supports expanded relationships, verify owner data
                if "owner" in pet_data:
                    assert pet_data["owner"]["id"] == user["id"]
                    assert pet_data["owner"]["email"] == user["email"]
                
            finally:
                await base_test.cleanup_test_resource(async_client, api_version, "pet", pet["id"])
        finally:
            await base_test.cleanup_test_resource(async_client, api_version, "user", user["id"])
```

## Feature-Specific Testing

### Health Records (v2+ Feature)

```python
from tests.dynamic.fixtures import parametrize_feature_versions

@parametrize_feature_versions("health_records")
class TestHealthRecords:
    """Test health records functionality (v2+ only)."""
    
    async def test_create_health_record(self, api_version: str, base_test: BaseVersionTest, async_client):
        """Test health record creation for pets."""
        # Create test pet first
        pet = await base_test.create_test_resource(async_client, api_version, "pet")
        
        try:
            # Create health record
            health_record_data = base_test.build_test_data(
                api_version, "health_record", "create",
                record_type="vaccination",
                description="Annual vaccination",
                date="2024-01-15",
                veterinarian="Dr. Smith"
            )
            
            endpoint = base_test.get_endpoint_url(api_version, "health_records", pet_id=pet["id"])
            response = await base_test.make_request("POST", endpoint, async_client, json=health_record_data)
            
            # Validate creation
            base_test.assert_status_code(response, 201, "Creating health record")
            health_record = response.json()
            
            # Validate structure
            base_test.validate_response_structure(health_record, api_version, "health_record")
            
            # Validate data
            assert health_record["record_type"] == health_record_data["record_type"]
            assert health_record["pet_id"] == pet["id"]
            
        finally:
            await base_test.cleanup_test_resource(async_client, api_version, "pet", pet["id"])
    
    async def test_health_record_history(self, api_version: str, base_test: BaseVersionTest, async_client):
        """Test retrieving pet health record history."""
        # Create test pet
        pet = await base_test.create_test_resource(async_client, api_version, "pet")
        
        try:
            # Create multiple health records
            records = []
            for i, record_type in enumerate(["vaccination", "checkup", "treatment"]):
                record_data = base_test.build_test_data(
                    api_version, "health_record", "create",
                    record_type=record_type,
                    description=f"Test {record_type} {i+1}",
                    date=f"2024-0{i+1}-15"
                )
                
                endpoint = base_test.get_endpoint_url(api_version, "health_records", pet_id=pet["id"])
                response = await base_test.make_request("POST", endpoint, async_client, json=record_data)
                records.append(response.json())
            
            # Get health record history
            history_response = await base_test.make_request("GET", endpoint, async_client)
            base_test.assert_status_code(history_response, 200, "Getting health record history")
            
            history = history_response.json()
            assert len(history) >= 3  # At least our test records
            
            # Validate each record in history
            for record in history:
                base_test.validate_response_structure(record, api_version, "health_record")
                assert record["pet_id"] == pet["id"]
            
        finally:
            await base_test.cleanup_test_resource(async_client, api_version, "pet", pet["id"])
```

### Statistics and Analytics (v2+ Feature)

```python
@parametrize_feature_versions("statistics")
class TestStatistics:
    """Test statistics and analytics functionality."""
    
    async def test_pet_statistics(self, api_version: str, base_test: BaseVersionTest, async_client):
        """Test pet statistics endpoint."""
        # Create test data
        pets = []
        for i in range(5):
            pet = await base_test.create_test_resource(
                async_client, api_version, "pet",
                name=f"Stats Pet {i+1}",
                species="dog" if i % 2 == 0 else "cat"
            )
            pets.append(pet)
        
        try:
            # Get statistics
            endpoint = base_test.get_endpoint_url(api_version, "statistics")
            response = await base_test.make_request("GET", endpoint, async_client, 
                                                  params={"type": "pets"})
            
            base_test.assert_status_code(response, 200, "Getting pet statistics")
            stats = response.json()
            
            # Validate statistics structure
            assert "total_pets" in stats
            assert "species_breakdown" in stats
            assert stats["total_pets"] >= 5  # At least our test pets
            
            # Validate species breakdown
            species_breakdown = stats["species_breakdown"]
            assert "dog" in species_breakdown
            assert "cat" in species_breakdown
            
        finally:
            # Cleanup test pets
            for pet in pets:
                await base_test.cleanup_test_resource(async_client, api_version, "pet", pet["id"])
    
    async def test_statistics_filtering(self, api_version: str, base_test: BaseVersionTest, async_client):
        """Test statistics with filtering parameters."""
        # Skip if enhanced filtering not available
        base_test.skip_if_feature_unavailable(api_version, "enhanced_filtering")
        
        # Create test pets with specific attributes
        test_pets = [
            {"name": "Filter Dog 1", "species": "dog", "breed": "labrador"},
            {"name": "Filter Dog 2", "species": "dog", "breed": "golden_retriever"},
            {"name": "Filter Cat 1", "species": "cat", "breed": "persian"},
        ]
        
        pets = []
        for pet_data in test_pets:
            pet = await base_test.create_test_resource(async_client, api_version, "pet", **pet_data)
            pets.append(pet)
        
        try:
            # Get filtered statistics
            endpoint = base_test.get_endpoint_url(api_version, "statistics")
            response = await base_test.make_request("GET", endpoint, async_client, 
                                                  params={
                                                      "type": "pets",
                                                      "species": "dog"
                                                  })
            
            base_test.assert_status_code(response, 200, "Getting filtered statistics")
            stats = response.json()
            
            # Validate filtered results
            assert "total_pets" in stats
            assert "breed_breakdown" in stats
            
            breed_breakdown = stats["breed_breakdown"]
            assert "labrador" in breed_breakdown
            assert "golden_retriever" in breed_breakdown
            assert "persian" not in breed_breakdown  # Should be filtered out
            
        finally:
            for pet in pets:
                await base_test.cleanup_test_resource(async_client, api_version, "pet", pet["id"])
```

## Error Handling and Validation

### Consistent Error Responses

```python
@parametrize_versions()
class TestErrorHandling:
    """Test error handling consistency across API versions."""
    
    async def test_not_found_errors(self, api_version: str, base_test: BaseVersionTest, async_client):
        """Test 404 error responses are consistent."""
        # Test pet not found
        endpoint = base_test.get_endpoint_url(api_version, "pets", "nonexistent-id")
        response = await base_test.make_request("GET", endpoint, async_client)
        base_test.assert_error_response(response, 404)
        
        # Test user not found
        endpoint = base_test.get_endpoint_url(api_version, "users", "nonexistent-id")
        response = await base_test.make_request("GET", endpoint, async_client)
        base_test.assert_error_response(response, 404)
    
    async def test_validation_errors(self, api_version: str, base_test: BaseVersionTest, async_client):
        """Test validation error responses."""
        # Test missing required fields
        invalid_data = {}  # Empty data should trigger validation errors
        endpoint = base_test.get_endpoint_url(api_version, "pets")
        response = await base_test.make_request("POST", endpoint, async_client, json=invalid_data)
        
        base_test.assert_error_response(response, 422)
        error_data = response.json()
        
        # Validate error structure
        assert "detail" in error_data or "errors" in error_data
        
        # Test invalid field values
        invalid_pet_data = base_test.build_test_data(
            api_version, "pet", "create",
            name="",  # Empty name should be invalid
            species="invalid_species",  # Invalid species
            weight=-5  # Negative weight should be invalid
        )
        
        response = await base_test.make_request("POST", endpoint, async_client, json=invalid_pet_data)
        base_test.assert_error_response(response, 422)
    
    async def test_authorization_errors(self, api_version: str, base_test: BaseVersionTest, async_client):
        """Test authorization error responses."""
        # Test without authentication (if required)
        endpoint = base_test.get_endpoint_url(api_version, "pets")
        
        # Remove auth headers if present
        headers = {k: v for k, v in async_client.headers.items() 
                  if k.lower() not in ['authorization', 'x-api-key']}
        
        response = await async_client.request("GET", endpoint, headers=headers)
        
        # Should get 401 (Unauthorized) or 403 (Forbidden)
        assert response.status_code in [401, 403], f"Expected 401 or 403, got {response.status_code}"
```

### Input Validation Testing

```python
@parametrize_versions()
class TestInputValidation:
    """Test input validation across different API versions."""
    
    async def test_field_length_validation(self, api_version: str, base_test: BaseVersionTest, async_client):
        """Test field length validation."""
        # Test name too long
        long_name = "x" * 1000  # Very long name
        pet_data = base_test.build_test_data(
            api_version, "pet", "create",
            name=long_name
        )
        
        endpoint = base_test.get_endpoint_url(api_version, "pets")
        response = await base_test.make_request("POST", endpoint, async_client, json=pet_data)
        
        # Should get validation error
        base_test.assert_error_response(response, 422)
    
    async def test_field_type_validation(self, api_version: str, base_test: BaseVersionTest, async_client):
        """Test field type validation."""
        # Test invalid data types
        invalid_pet_data = {
            "name": 123,  # Should be string
            "species": ["dog"],  # Should be string, not array
            "weight": "not_a_number",  # Should be number
            "owner_id": "not_an_id"  # Should be valid ID
        }
        
        endpoint = base_test.get_endpoint_url(api_version, "pets")
        response = await base_test.make_request("POST", endpoint, async_client, json=invalid_pet_data)
        
        base_test.assert_error_response(response, 422)
    
    async def test_version_specific_validation(self, api_version: str, base_test: BaseVersionTest, async_client):
        """Test version-specific field validation."""
        # Get version-specific fields
        schema_fields = base_test.config_manager.get_schema_fields(api_version, "pet_create")
        
        # Test with field that doesn't exist in this version
        pet_data = base_test.build_test_data(api_version, "pet", "create")
        
        if api_version == "v1":
            # Add v2-only field to v1 request
            pet_data["temperament"] = "friendly"
        
        endpoint = base_test.get_endpoint_url(api_version, "pets")
        response = await base_test.make_request("POST", endpoint, async_client, json=pet_data)
        
        if api_version == "v1":
            # v1 should either ignore unknown fields or return validation error
            assert response.status_code in [201, 422]
        else:
            # v2+ should accept the field
            base_test.assert_status_code(response, 201, "Creating pet with version-appropriate fields")
            if response.status_code == 201:
                await base_test.cleanup_test_resource(async_client, api_version, "pet", response.json()["id"])
```

## Data Consistency Across Versions

### Cross-Version Data Integrity

```python
@parametrize_versions()
class TestDataConsistency:
    """Test data consistency and integrity across API versions."""
    
    async def test_business_logic_consistency(self, api_version: str, base_test: BaseVersionTest, async_client):
        """Test that business logic remains consistent across versions."""
        # Create pet with same core data across versions
        core_pet_data = {
            "name": "Consistency Test Pet",
            "species": "dog",
            "breed": "labrador",
            "weight": 25.5
        }
        
        pet_data = base_test.build_test_data(api_version, "pet", "create", **core_pet_data)
        
        # Create pet
        endpoint = base_test.get_endpoint_url(api_version, "pets")
        response = await base_test.make_request("POST", endpoint, async_client, json=pet_data)
        base_test.assert_status_code(response, 201, "Creating pet for consistency test")
        
        pet = response.json()
        
        try:
            # Verify core business rules are consistent
            assert pet["name"] == core_pet_data["name"]
            assert pet["species"] == core_pet_data["species"]
            assert pet["breed"] == core_pet_data["breed"]
            assert pet["weight"] == core_pet_data["weight"]
            
            # Verify calculated fields (if any) are consistent
            if "age_category" in pet:
                # Business logic: pets under 1 year are "puppy", 1-7 are "adult", 7+ are "senior"
                # This logic should be consistent across versions
                assert pet["age_category"] in ["puppy", "adult", "senior"]
            
            # Test update consistency
            update_data = {"weight": 30.0}
            update_response = await base_test.make_request("PUT", 
                                                         base_test.get_endpoint_url(api_version, "pets", pet["id"]), 
                                                         async_client, json=update_data)
            
            base_test.assert_status_code(update_response, 200, "Updating pet weight")
            updated_pet = update_response.json()
            assert updated_pet["weight"] == 30.0
            
        finally:
            await base_test.cleanup_test_resource(async_client, api_version, "pet", pet["id"])
    
    async def test_data_migration_compatibility(self, api_version: str, base_test: BaseVersionTest, async_client):
        """Test that data created in one version is accessible in others."""
        # This test would typically involve creating data in one version
        # and verifying it's accessible/correct in another version
        # For this example, we'll test field compatibility
        
        # Create pet with minimal required fields
        minimal_pet_data = {
            "name": "Migration Test Pet",
            "species": "cat",
            "owner_id": 1
        }
        
        pet_data = base_test.build_test_data(api_version, "pet", "create", **minimal_pet_data)
        
        endpoint = base_test.get_endpoint_url(api_version, "pets")
        response = await base_test.make_request("POST", endpoint, async_client, json=pet_data)
        base_test.assert_status_code(response, 201, "Creating pet with minimal data")
        
        pet = response.json()
        
        try:
            # Verify that all versions can read this pet
            get_response = await base_test.make_request("GET", 
                                                      base_test.get_endpoint_url(api_version, "pets", pet["id"]), 
                                                      async_client)
            
            base_test.assert_status_code(get_response, 200, "Reading pet")
            retrieved_pet = get_response.json()
            
            # Verify core fields are present
            assert retrieved_pet["name"] == minimal_pet_data["name"]
            assert retrieved_pet["species"] == minimal_pet_data["species"]
            
            # Verify version-specific fields have appropriate defaults
            base_test.validate_response_structure(retrieved_pet, api_version, "pet")
            
        finally:
            await base_test.cleanup_test_resource(async_client, api_version, "pet", pet["id"])
```

## Batch Operations

### Batch Processing (v2+ Feature)

```python
@parametrize_feature_versions("batch_operations")
class TestBatchOperations:
    """Test batch operations functionality (v2+ only)."""
    
    async def test_batch_create_pets(self, api_version: str, base_test: BaseVersionTest, async_client):
        """Test batch creation of multiple pets."""
        # Prepare batch data
        batch_data = []
        for i in range(3):
            pet_data = base_test.build_test_data(
                api_version, "pet", "create",
                name=f"Batch Pet {i+1}",
                species="dog" if i % 2 == 0 else "cat"
            )
            batch_data.append(pet_data)
        
        # Send batch create request
        endpoint = base_test.get_endpoint_url(api_version, "pets", batch=True)
        response = await base_test.make_request("POST", endpoint, async_client, 
                                              json={"pets": batch_data})
        
        base_test.assert_status_code(response, 201, "Batch creating pets")
        result = response.json()
        
        # Validate batch response
        assert "created" in result
        assert len(result["created"]) == 3
        
        created_pets = result["created"]
        
        try:
            # Validate each created pet
            for i, pet in enumerate(created_pets):
                base_test.validate_response_structure(pet, api_version, "pet")
                assert pet["name"] == f"Batch Pet {i+1}"
            
            # Verify pets were actually created
            for pet in created_pets:
                get_response = await base_test.make_request("GET", 
                                                          base_test.get_endpoint_url(api_version, "pets", pet["id"]), 
                                                          async_client)
                base_test.assert_status_code(get_response, 200, f"Verifying batch created pet {pet['id']}")
        
        finally:
            # Cleanup batch created pets
            for pet in created_pets:
                await base_test.cleanup_test_resource(async_client, api_version, "pet", pet["id"])
    
    async def test_batch_update_pets(self, api_version: str, base_test: BaseVersionTest, async_client):
        """Test batch updates of multiple pets."""
        # Create test pets first
        pets = []
        for i in range(3):
            pet = await base_test.create_test_resource(
                async_client, api_version, "pet",
                name=f"Batch Update Pet {i+1}"
            )
            pets.append(pet)
        
        try:
            # Prepare batch update data
            batch_updates = []
            for pet in pets:
                update_data = {
                    "id": pet["id"],
                    "name": f"Updated {pet['name']}",
                    "breed": "updated_breed"
                }
                batch_updates.append(update_data)
            
            # Send batch update request
            endpoint = base_test.get_endpoint_url(api_version, "pets", batch=True)
            response = await base_test.make_request("PUT", endpoint, async_client, 
                                                  json={"updates": batch_updates})
            
            base_test.assert_status_code(response, 200, "Batch updating pets")
            result = response.json()
            
            # Validate batch update response
            assert "updated" in result
            assert len(result["updated"]) == 3
            
            # Verify updates were applied
            for pet in pets:
                get_response = await base_test.make_request("GET", 
                                                          base_test.get_endpoint_url(api_version, "pets", pet["id"]), 
                                                          async_client)
                updated_pet = get_response.json()
                assert updated_pet["name"].startswith("Updated")
                assert updated_pet["breed"] == "updated_breed"
        
        finally:
            # Cleanup test pets
            for pet in pets:
                await base_test.cleanup_test_resource(async_client, api_version, "pet", pet["id"])
```

## Search and Filtering

### Enhanced Filtering (v2+ Feature)

```python
@parametrize_feature_versions("enhanced_filtering")
class TestEnhancedFiltering:
    """Test enhanced filtering and search functionality."""
    
    async def test_advanced_pet_filtering(self, api_version: str, base_test: BaseVersionTest, async_client):
        """Test advanced filtering options for pets."""
        # Create diverse test data
        test_pets_data = [
            {"name": "Filter Dog 1", "species": "dog", "breed": "labrador", "weight": 25.0},
            {"name": "Filter Dog 2", "species": "dog", "breed": "golden_retriever", "weight": 30.0},
            {"name": "Filter Cat 1", "species": "cat", "breed": "persian", "weight": 4.5},
            {"name": "Filter Cat 2", "species": "cat", "breed": "siamese", "weight": 3.8},
        ]
        
        pets = []
        for pet_data in test_pets_data:
            pet = await base_test.create_test_resource(async_client, api_version, "pet", **pet_data)
            pets.append(pet)
        
        try:
            # Test species filtering
            endpoint = base_test.get_endpoint_url(api_version, "pets")
            response = await base_test.make_request("GET", endpoint, async_client, 
                                                  params={"species": "dog"})
            
            base_test.assert_status_code(response, 200, "Filtering pets by species")
            filtered_pets = response.json()
            
            # Validate filtering results
            items = filtered_pets if isinstance(filtered_pets, list) else filtered_pets["items"]
            dog_pets = [pet for pet in items if pet["species"] == "dog"]
            assert len(dog_pets) >= 2  # At least our test dogs
            
            # Test weight range filtering
            response = await base_test.make_request("GET", endpoint, async_client, 
                                                  params={
                                                      "weight_min": 20.0,
                                                      "weight_max": 35.0
                                                  })
            
            base_test.assert_status_code(response, 200, "Filtering pets by weight range")
            weight_filtered = response.json()
            
            items = weight_filtered if isinstance(weight_filtered, list) else weight_filtered["items"]
            for pet in items:
                if pet["id"] in [p["id"] for p in pets]:  # Only check our test pets
                    assert 20.0 <= pet["weight"] <= 35.0
            
            # Test combined filtering
            response = await base_test.make_request("GET", endpoint, async_client, 
                                                  params={
                                                      "species": "dog",
                                                      "breed": "labrador"
                                                  })
            
            base_test.assert_status_code(response, 200, "Combined filtering")
            combined_filtered = response.json()
            
            items = combined_filtered if isinstance(combined_filtered, list) else combined_filtered["items"]
            labrador_dogs = [pet for pet in items if pet["species"] == "dog" and pet["breed"] == "labrador"]
            assert len(labrador_dogs) >= 1  # At least our test labrador
        
        finally:
            # Cleanup test pets
            for pet in pets:
                await base_test.cleanup_test_resource(async_client, api_version, "pet", pet["id"])
    
    async def test_search_functionality(self, api_version: str, base_test: BaseVersionTest, async_client):
        """Test search functionality across pet names and descriptions."""
        # Create pets with searchable content
        searchable_pets = [
            {"name": "Fluffy Search Test", "species": "cat"},
            {"name": "Buddy Search Test", "species": "dog"},
            {"name": "Max Normal Pet", "species": "dog"},
        ]
        
        pets = []
        for pet_data in searchable_pets:
            pet = await base_test.create_test_resource(async_client, api_version, "pet", **pet_data)
            pets.append(pet)
        
        try:
            # Test name search
            endpoint = base_test.get_endpoint_url(api_version, "pets")
            response = await base_test.make_request("GET", endpoint, async_client, 
                                                  params={"search": "Search Test"})
            
            base_test.assert_status_code(response, 200, "Searching pets by name")
            search_results = response.json()
            
            items = search_results if isinstance(search_results, list) else search_results["items"]
            matching_pets = [pet for pet in items if "Search Test" in pet["name"]]
            assert len(matching_pets) >= 2  # Should find Fluffy and Buddy
            
            # Test partial name search
            response = await base_test.make_request("GET", endpoint, async_client, 
                                                  params={"search": "Fluffy"})
            
            base_test.assert_status_code(response, 200, "Partial name search")
            partial_results = response.json()
            
            items = partial_results if isinstance(partial_results, list) else partial_results["items"]
            fluffy_pets = [pet for pet in items if "Fluffy" in pet["name"]]
            assert len(fluffy_pets) >= 1
        
        finally:
            # Cleanup test pets
            for pet in pets:
                await base_test.cleanup_test_resource(async_client, api_version, "pet", pet["id"])
```

## Complex Workflows

### Multi-Step Business Processes

```python
@parametrize_versions()
class TestComplexWorkflows:
    """Test complex multi-step business workflows."""
    
    async def test_appointment_booking_workflow(self, api_version: str, base_test: BaseVersionTest, async_client):
        """Test complete appointment booking workflow."""
        # Step 1: Create user (pet owner)
        user = await base_test.create_test_resource(
            async_client, api_version, "user",
            email="workflow@example.com",
            first_name="Workflow",
            last_name="Test"
        )
        
        try:
            # Step 2: Create pet
            pet = await base_test.create_test_resource(
                async_client, api_version, "pet",
                name="Workflow Pet",
                species="dog",
                owner_id=user["id"]
            )
            
            try:
                # Step 3: Book appointment
                appointment_data = base_test.build_test_data(
                    api_version, "appointment", "create",
                    pet_id=pet["id"],
                    user_id=user["id"],
                    appointment_type="checkup",
                    scheduled_date="2024-12-01T10:00:00Z",
                    notes="Regular checkup appointment"
                )
                
                appointment_endpoint = base_test.get_endpoint_url(api_version, "appointments")
                appointment_response = await base_test.make_request("POST", appointment_endpoint, 
                                                                  async_client, json=appointment_data)
                
                base_test.assert_status_code(appointment_response, 201, "Booking appointment")
                appointment = appointment_response.json()
                
                try:
                    # Step 4: Verify appointment relationships
                    assert appointment["pet_id"] == pet["id"]
                    assert appointment["user_id"] == user["id"]
                    
                    # Step 5: Update appointment status
                    update_data = {"status": "confirmed"}
                    update_response = await base_test.make_request("PUT", 
                                                                 base_test.get_endpoint_url(api_version, "appointments", appointment["id"]), 
                                                                 async_client, json=update_data)
                    
                    base_test.assert_status_code(update_response, 200, "Confirming appointment")
                    updated_appointment = update_response.json()
                    assert updated_appointment["status"] == "confirmed"
                    
                    # Step 6: Add health record after appointment (if supported)
                    if base_test.should_test_feature(api_version, "health_records"):
                        health_record_data = base_test.build_test_data(
                            api_version, "health_record", "create",
                            record_type="checkup",
                            description="Regular checkup completed",
                            appointment_id=appointment["id"]
                        )
                        
                        health_endpoint = base_test.get_endpoint_url(api_version, "health_records", pet_id=pet["id"])
                        health_response = await base_test.make_request("POST", health_endpoint, 
                                                                     async_client, json=health_record_data)
                        
                        base_test.assert_status_code(health_response, 201, "Adding health record")
                
                finally:
                    await base_test.cleanup_test_resource(async_client, api_version, "appointment", appointment["id"])
            
            finally:
                await base_test.cleanup_test_resource(async_client, api_version, "pet", pet["id"])
        
        finally:
            await base_test.cleanup_test_resource(async_client, api_version, "user", user["id"])
```

This comprehensive documentation covers the most common testing scenarios you'll encounter when using the dynamic API testing framework. Each example demonstrates best practices for version-agnostic testing while handling version-specific features and behaviors appropriately.