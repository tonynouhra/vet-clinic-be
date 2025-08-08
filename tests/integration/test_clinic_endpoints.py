"""
Integration tests for Clinic API endpoints.

Tests the complete API flow from HTTP request to database operations
for clinic and veterinarian management functionality.
"""

import pytest
import uuid
from datetime import time
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.user import User, UserRole
from app.models.clinic import (
    Clinic, Veterinarian, VeterinarianAvailability, ClinicReview, VeterinarianReview,
    ClinicType, VeterinarianSpecialty, DayOfWeek
)
from tests.conftest import create_test_user, get_auth_headers


@pytest.mark.asyncio
async def test_list_clinics_basic(async_client: AsyncClient, test_db: AsyncSession):
    """Test basic clinic listing endpoint."""
    # Create test user
    user = await create_test_user(test_db, role=UserRole.PET_OWNER)
    headers = get_auth_headers(user)
    
    # Create test clinic
    clinic = Clinic(
        name="Test Veterinary Clinic",
        clinic_type=ClinicType.GENERAL_PRACTICE,
        description="A test clinic",
        phone_number="555-0123",
        email="test@clinic.com",
        address_line1="123 Main St",
        city="Test City",
        state="Test State",
        zip_code="12345",
        country="United States",
        latitude=40.7128,
        longitude=-74.0060,
        is_emergency_clinic=False,
        is_24_hour=False,
        is_active=True,
        is_accepting_new_patients=True
    )
    test_db.add(clinic)
    await test_db.commit()
    await test_db.refresh(clinic)
    
    # Test endpoint
    response = await async_client.get("/api/v1/clinics", headers=headers)
    
    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["version"] == "v1"
    assert "data" in data
    
    clinic_data = data["data"]
    assert clinic_data["total"] == 1
    assert len(clinic_data["clinics"]) == 1
    
    clinic_response = clinic_data["clinics"][0]
    assert clinic_response["name"] == "Test Veterinary Clinic"
    assert clinic_response["clinic_type"] == "general_practice"
    assert clinic_response["city"] == "Test City"
    assert clinic_response["state"] == "Test State"


@pytest.mark.asyncio
async def test_list_clinics_with_filters(async_client: AsyncClient, test_db: AsyncSession):
    """Test clinic listing with filters."""
    # Create test user
    user = await create_test_user(test_db, role=UserRole.PET_OWNER)
    headers = get_auth_headers(user)
    
    # Create test clinics
    clinic1 = Clinic(
        name="General Practice Clinic",
        clinic_type=ClinicType.GENERAL_PRACTICE,
        phone_number="555-0123",
        address_line1="123 Main St",
        city="Test City",
        state="Test State",
        zip_code="12345",
        is_emergency_clinic=False,
        is_active=True
    )
    
    clinic2 = Clinic(
        name="Emergency Animal Hospital",
        clinic_type=ClinicType.EMERGENCY_CLINIC,
        phone_number="555-0124",
        address_line1="456 Oak St",
        city="Other City",
        state="Test State",
        zip_code="12346",
        is_emergency_clinic=True,
        is_active=True
    )
    
    test_db.add_all([clinic1, clinic2])
    await test_db.commit()
    
    # Test filtering by clinic type
    response = await async_client.get(
        "/api/v1/clinics?clinic_type=emergency_clinic",
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["total"] == 1
    assert data["data"]["clinics"][0]["name"] == "Emergency Animal Hospital"
    
    # Test filtering by city
    response = await async_client.get(
        "/api/v1/clinics?city=Test City",
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["total"] == 1
    assert data["data"]["clinics"][0]["name"] == "General Practice Clinic"


@pytest.mark.asyncio
async def test_list_clinics_location_search(async_client: AsyncClient, test_db: AsyncSession):
    """Test clinic listing with location-based search."""
    # Create test user
    user = await create_test_user(test_db, role=UserRole.PET_OWNER)
    headers = get_auth_headers(user)
    
    # Create test clinic with coordinates
    clinic = Clinic(
        name="NYC Veterinary Clinic",
        clinic_type=ClinicType.GENERAL_PRACTICE,
        phone_number="555-0123",
        address_line1="123 Broadway",
        city="New York",
        state="NY",
        zip_code="10001",
        latitude=40.7128,
        longitude=-74.0060,
        is_active=True
    )
    test_db.add(clinic)
    await test_db.commit()
    
    # Test location search
    response = await async_client.get(
        "/api/v1/clinics?latitude=40.7128&longitude=-74.0060&radius_miles=10",
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["total"] == 1
    assert data["data"]["clinics"][0]["name"] == "NYC Veterinary Clinic"


@pytest.mark.asyncio
async def test_get_clinic_by_id(async_client: AsyncClient, test_db: AsyncSession):
    """Test getting clinic by ID."""
    # Create test user
    user = await create_test_user(test_db, role=UserRole.PET_OWNER)
    headers = get_auth_headers(user)
    
    # Create test clinic
    clinic = Clinic(
        name="Test Clinic",
        clinic_type=ClinicType.GENERAL_PRACTICE,
        phone_number="555-0123",
        address_line1="123 Main St",
        city="Test City",
        state="Test State",
        zip_code="12345",
        is_active=True
    )
    test_db.add(clinic)
    await test_db.commit()
    await test_db.refresh(clinic)
    
    # Test endpoint
    response = await async_client.get(f"/api/v1/clinics/{clinic.id}", headers=headers)
    
    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["name"] == "Test Clinic"
    assert data["data"]["id"] == str(clinic.id)


@pytest.mark.asyncio
async def test_get_clinic_not_found(async_client: AsyncClient, test_db: AsyncSession):
    """Test getting non-existent clinic."""
    # Create test user
    user = await create_test_user(test_db, role=UserRole.PET_OWNER)
    headers = get_auth_headers(user)
    
    # Test with non-existent ID
    fake_id = uuid.uuid4()
    response = await async_client.get(f"/api/v1/clinics/{fake_id}", headers=headers)
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_list_veterinarians_basic(async_client: AsyncClient, test_db: AsyncSession):
    """Test basic veterinarian listing endpoint."""
    # Create test user and veterinarian user
    user = await create_test_user(test_db, role=UserRole.PET_OWNER)
    vet_user = await create_test_user(test_db, role=UserRole.VETERINARIAN, email="vet@test.com")
    headers = get_auth_headers(user)
    
    # Create test clinic
    clinic = Clinic(
        name="Test Clinic",
        clinic_type=ClinicType.GENERAL_PRACTICE,
        phone_number="555-0123",
        address_line1="123 Main St",
        city="Test City",
        state="Test State",
        zip_code="12345",
        is_active=True
    )
    test_db.add(clinic)
    await test_db.commit()
    await test_db.refresh(clinic)
    
    # Create test veterinarian
    veterinarian = Veterinarian(
        user_id=vet_user.id,
        clinic_id=clinic.id,
        license_number="VET123456",
        years_of_experience=5,
        bio="Experienced veterinarian",
        consultation_fee=150.0,
        is_available_for_emergency=True,
        is_accepting_new_patients=True,
        is_active=True
    )
    test_db.add(veterinarian)
    await test_db.commit()
    await test_db.refresh(veterinarian)
    
    # Test endpoint
    response = await async_client.get("/api/v1/veterinarians", headers=headers)
    
    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["version"] == "v1"
    
    vet_data = data["data"]
    assert vet_data["total"] == 1
    assert len(vet_data["veterinarians"]) == 1
    
    vet_response = vet_data["veterinarians"][0]
    assert vet_response["license_number"] == "VET123456"
    assert vet_response["years_of_experience"] == 5
    assert vet_response["is_available_for_emergency"] is True


@pytest.mark.asyncio
async def test_list_veterinarians_with_filters(async_client: AsyncClient, test_db: AsyncSession):
    """Test veterinarian listing with filters."""
    # Create test user and veterinarian users
    user = await create_test_user(test_db, role=UserRole.PET_OWNER)
    vet_user1 = await create_test_user(test_db, role=UserRole.VETERINARIAN, email="vet1@test.com")
    vet_user2 = await create_test_user(test_db, role=UserRole.VETERINARIAN, email="vet2@test.com")
    headers = get_auth_headers(user)
    
    # Create test clinic
    clinic = Clinic(
        name="Test Clinic",
        clinic_type=ClinicType.GENERAL_PRACTICE,
        phone_number="555-0123",
        address_line1="123 Main St",
        city="Test City",
        state="Test State",
        zip_code="12345",
        is_active=True
    )
    test_db.add(clinic)
    await test_db.commit()
    await test_db.refresh(clinic)
    
    # Create test veterinarians
    vet1 = Veterinarian(
        user_id=vet_user1.id,
        clinic_id=clinic.id,
        license_number="VET123456",
        years_of_experience=5,
        is_available_for_emergency=True,
        is_active=True
    )
    
    vet2 = Veterinarian(
        user_id=vet_user2.id,
        clinic_id=clinic.id,
        license_number="VET789012",
        years_of_experience=10,
        is_available_for_emergency=False,
        is_active=True
    )
    
    test_db.add_all([vet1, vet2])
    await test_db.commit()
    
    # Test filtering by emergency availability
    response = await async_client.get(
        "/api/v1/veterinarians?is_available_for_emergency=true",
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["total"] == 1
    assert data["data"]["veterinarians"][0]["license_number"] == "VET123456"
    
    # Test filtering by minimum experience
    response = await async_client.get(
        "/api/v1/veterinarians?min_experience_years=8",
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["total"] == 1
    assert data["data"]["veterinarians"][0]["license_number"] == "VET789012"


@pytest.mark.asyncio
async def test_get_veterinarian_by_id(async_client: AsyncClient, test_db: AsyncSession):
    """Test getting veterinarian by ID."""
    # Create test user and veterinarian user
    user = await create_test_user(test_db, role=UserRole.PET_OWNER)
    vet_user = await create_test_user(test_db, role=UserRole.VETERINARIAN, email="vet@test.com")
    headers = get_auth_headers(user)
    
    # Create test clinic
    clinic = Clinic(
        name="Test Clinic",
        clinic_type=ClinicType.GENERAL_PRACTICE,
        phone_number="555-0123",
        address_line1="123 Main St",
        city="Test City",
        state="Test State",
        zip_code="12345",
        is_active=True
    )
    test_db.add(clinic)
    await test_db.commit()
    await test_db.refresh(clinic)
    
    # Create test veterinarian
    veterinarian = Veterinarian(
        user_id=vet_user.id,
        clinic_id=clinic.id,
        license_number="VET123456",
        years_of_experience=5,
        bio="Experienced veterinarian",
        is_active=True
    )
    test_db.add(veterinarian)
    await test_db.commit()
    await test_db.refresh(veterinarian)
    
    # Test endpoint
    response = await async_client.get(f"/api/v1/veterinarians/{veterinarian.id}", headers=headers)
    
    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["license_number"] == "VET123456"
    assert data["data"]["id"] == str(veterinarian.id)


@pytest.mark.asyncio
async def test_search_veterinarians_by_location(async_client: AsyncClient, test_db: AsyncSession):
    """Test location-based veterinarian search."""
    # Create test user and veterinarian user
    user = await create_test_user(test_db, role=UserRole.PET_OWNER)
    vet_user = await create_test_user(test_db, role=UserRole.VETERINARIAN, email="vet@test.com")
    headers = get_auth_headers(user)
    
    # Create test clinic with coordinates
    clinic = Clinic(
        name="NYC Vet Clinic",
        clinic_type=ClinicType.GENERAL_PRACTICE,
        phone_number="555-0123",
        address_line1="123 Broadway",
        city="New York",
        state="NY",
        zip_code="10001",
        latitude=40.7128,
        longitude=-74.0060,
        is_active=True
    )
    test_db.add(clinic)
    await test_db.commit()
    await test_db.refresh(clinic)
    
    # Create test veterinarian
    veterinarian = Veterinarian(
        user_id=vet_user.id,
        clinic_id=clinic.id,
        license_number="VET123456",
        years_of_experience=5,
        is_active=True
    )
    test_db.add(veterinarian)
    await test_db.commit()
    
    # Test location search
    response = await async_client.get(
        "/api/v1/veterinarians/search/location?latitude=40.7128&longitude=-74.0060&radius_miles=10",
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["total"] == 1
    assert data["data"]["veterinarians"][0]["license_number"] == "VET123456"


@pytest.mark.asyncio
async def test_get_veterinarian_availability(async_client: AsyncClient, test_db: AsyncSession):
    """Test getting veterinarian availability."""
    # Create test user and veterinarian user
    user = await create_test_user(test_db, role=UserRole.PET_OWNER)
    vet_user = await create_test_user(test_db, role=UserRole.VETERINARIAN, email="vet@test.com")
    headers = get_auth_headers(user)
    
    # Create test clinic
    clinic = Clinic(
        name="Test Clinic",
        clinic_type=ClinicType.GENERAL_PRACTICE,
        phone_number="555-0123",
        address_line1="123 Main St",
        city="Test City",
        state="Test State",
        zip_code="12345",
        is_active=True
    )
    test_db.add(clinic)
    await test_db.commit()
    await test_db.refresh(clinic)
    
    # Create test veterinarian
    veterinarian = Veterinarian(
        user_id=vet_user.id,
        clinic_id=clinic.id,
        license_number="VET123456",
        is_active=True
    )
    test_db.add(veterinarian)
    await test_db.commit()
    await test_db.refresh(veterinarian)
    
    # Create test availability
    availability = VeterinarianAvailability(
        veterinarian_id=veterinarian.id,
        day_of_week=DayOfWeek.MONDAY,
        is_available=True,
        start_time=time(9, 0),
        end_time=time(17, 0),
        default_appointment_duration=30
    )
    test_db.add(availability)
    await test_db.commit()
    
    # Test endpoint
    response = await async_client.get(
        f"/api/v1/veterinarians/{veterinarian.id}/availability",
        headers=headers
    )
    
    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) == 1
    
    avail_data = data["data"][0]
    assert avail_data["day_of_week"] == "monday"
    assert avail_data["is_available"] is True
    assert avail_data["start_time"] == "09:00:00"
    assert avail_data["end_time"] == "17:00:00"


@pytest.mark.asyncio
async def test_update_veterinarian_availability(async_client: AsyncClient, test_db: AsyncSession):
    """Test updating veterinarian availability."""
    # Create test veterinarian user
    vet_user = await create_test_user(test_db, role=UserRole.VETERINARIAN, email="vet@test.com")
    headers = get_auth_headers(vet_user)
    
    # Create test clinic
    clinic = Clinic(
        name="Test Clinic",
        clinic_type=ClinicType.GENERAL_PRACTICE,
        phone_number="555-0123",
        address_line1="123 Main St",
        city="Test City",
        state="Test State",
        zip_code="12345",
        is_active=True
    )
    test_db.add(clinic)
    await test_db.commit()
    await test_db.refresh(clinic)
    
    # Create test veterinarian
    veterinarian = Veterinarian(
        user_id=vet_user.id,
        clinic_id=clinic.id,
        license_number="VET123456",
        is_active=True
    )
    test_db.add(veterinarian)
    await test_db.commit()
    await test_db.refresh(veterinarian)
    
    # Test data
    availability_data = {
        "availability": [
            {
                "day_of_week": "monday",
                "is_available": True,
                "start_time": "09:00:00",
                "end_time": "17:00:00",
                "default_appointment_duration": 30
            },
            {
                "day_of_week": "tuesday",
                "is_available": True,
                "start_time": "10:00:00",
                "end_time": "18:00:00",
                "default_appointment_duration": 45
            }
        ]
    }
    
    # Test endpoint
    response = await async_client.put(
        f"/api/v1/veterinarians/{veterinarian.id}/availability",
        json=availability_data,
        headers=headers
    )
    
    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) == 2
    
    # Check Monday availability
    monday_avail = next(a for a in data["data"] if a["day_of_week"] == "monday")
    assert monday_avail["start_time"] == "09:00:00"
    assert monday_avail["end_time"] == "17:00:00"
    assert monday_avail["default_appointment_duration"] == 30
    
    # Check Tuesday availability
    tuesday_avail = next(a for a in data["data"] if a["day_of_week"] == "tuesday")
    assert tuesday_avail["start_time"] == "10:00:00"
    assert tuesday_avail["end_time"] == "18:00:00"
    assert tuesday_avail["default_appointment_duration"] == 45


@pytest.mark.asyncio
async def test_create_clinic_review(async_client: AsyncClient, test_db: AsyncSession):
    """Test creating a clinic review."""
    # Create test user
    user = await create_test_user(test_db, role=UserRole.PET_OWNER)
    headers = get_auth_headers(user)
    
    # Create test clinic
    clinic = Clinic(
        name="Test Clinic",
        clinic_type=ClinicType.GENERAL_PRACTICE,
        phone_number="555-0123",
        address_line1="123 Main St",
        city="Test City",
        state="Test State",
        zip_code="12345",
        is_active=True
    )
    test_db.add(clinic)
    await test_db.commit()
    await test_db.refresh(clinic)
    
    # Test data
    review_data = {
        "rating": 5,
        "title": "Great clinic!",
        "review_text": "Excellent service and care for my pet.",
        "is_anonymous": False
    }
    
    # Test endpoint
    response = await async_client.post(
        f"/api/v1/clinics/{clinic.id}/reviews",
        json=review_data,
        headers=headers
    )
    
    # Assertions
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["rating"] == 5
    assert data["data"]["title"] == "Great clinic!"
    assert data["data"]["review_text"] == "Excellent service and care for my pet."
    assert data["data"]["clinic_id"] == str(clinic.id)
    assert data["data"]["reviewer_id"] == str(user.id)


@pytest.mark.asyncio
async def test_create_veterinarian_review(async_client: AsyncClient, test_db: AsyncSession):
    """Test creating a veterinarian review."""
    # Create test user and veterinarian user
    user = await create_test_user(test_db, role=UserRole.PET_OWNER)
    vet_user = await create_test_user(test_db, role=UserRole.VETERINARIAN, email="vet@test.com")
    headers = get_auth_headers(user)
    
    # Create test clinic
    clinic = Clinic(
        name="Test Clinic",
        clinic_type=ClinicType.GENERAL_PRACTICE,
        phone_number="555-0123",
        address_line1="123 Main St",
        city="Test City",
        state="Test State",
        zip_code="12345",
        is_active=True
    )
    test_db.add(clinic)
    await test_db.commit()
    await test_db.refresh(clinic)
    
    # Create test veterinarian
    veterinarian = Veterinarian(
        user_id=vet_user.id,
        clinic_id=clinic.id,
        license_number="VET123456",
        is_active=True
    )
    test_db.add(veterinarian)
    await test_db.commit()
    await test_db.refresh(veterinarian)
    
    # Test data
    review_data = {
        "rating": 5,
        "title": "Excellent veterinarian!",
        "review_text": "Very knowledgeable and caring with my pet.",
        "bedside_manner_rating": 5,
        "expertise_rating": 5,
        "communication_rating": 4,
        "is_anonymous": False
    }
    
    # Test endpoint
    response = await async_client.post(
        f"/api/v1/veterinarians/{veterinarian.id}/reviews",
        json=review_data,
        headers=headers
    )
    
    # Assertions
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["rating"] == 5
    assert data["data"]["title"] == "Excellent veterinarian!"
    assert data["data"]["bedside_manner_rating"] == 5
    assert data["data"]["expertise_rating"] == 5
    assert data["data"]["communication_rating"] == 4
    assert data["data"]["veterinarian_id"] == str(veterinarian.id)
    assert data["data"]["reviewer_id"] == str(user.id)


@pytest.mark.asyncio
async def test_get_clinic_reviews(async_client: AsyncClient, test_db: AsyncSession):
    """Test getting clinic reviews."""
    # Create test user
    user = await create_test_user(test_db, role=UserRole.PET_OWNER)
    headers = get_auth_headers(user)
    
    # Create test clinic
    clinic = Clinic(
        name="Test Clinic",
        clinic_type=ClinicType.GENERAL_PRACTICE,
        phone_number="555-0123",
        address_line1="123 Main St",
        city="Test City",
        state="Test State",
        zip_code="12345",
        is_active=True
    )
    test_db.add(clinic)
    await test_db.commit()
    await test_db.refresh(clinic)
    
    # Create test review
    review = ClinicReview(
        clinic_id=clinic.id,
        reviewer_id=user.id,
        rating=5,
        title="Great clinic!",
        review_text="Excellent service.",
        is_verified=False,
        is_anonymous=False
    )
    test_db.add(review)
    await test_db.commit()
    
    # Test endpoint
    response = await async_client.get(f"/api/v1/clinics/{clinic.id}/reviews", headers=headers)
    
    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["total"] == 1
    assert len(data["data"]["reviews"]) == 1
    
    review_data = data["data"]["reviews"][0]
    assert review_data["rating"] == 5
    assert review_data["title"] == "Great clinic!"
    assert review_data["clinic_id"] == str(clinic.id)


@pytest.mark.asyncio
async def test_get_veterinarian_reviews(async_client: AsyncClient, test_db: AsyncSession):
    """Test getting veterinarian reviews."""
    # Create test user and veterinarian user
    user = await create_test_user(test_db, role=UserRole.PET_OWNER)
    vet_user = await create_test_user(test_db, role=UserRole.VETERINARIAN, email="vet@test.com")
    headers = get_auth_headers(user)
    
    # Create test clinic
    clinic = Clinic(
        name="Test Clinic",
        clinic_type=ClinicType.GENERAL_PRACTICE,
        phone_number="555-0123",
        address_line1="123 Main St",
        city="Test City",
        state="Test State",
        zip_code="12345",
        is_active=True
    )
    test_db.add(clinic)
    await test_db.commit()
    await test_db.refresh(clinic)
    
    # Create test veterinarian
    veterinarian = Veterinarian(
        user_id=vet_user.id,
        clinic_id=clinic.id,
        license_number="VET123456",
        is_active=True
    )
    test_db.add(veterinarian)
    await test_db.commit()
    await test_db.refresh(veterinarian)
    
    # Create test review
    review = VeterinarianReview(
        veterinarian_id=veterinarian.id,
        reviewer_id=user.id,
        rating=5,
        title="Excellent vet!",
        review_text="Very professional.",
        bedside_manner_rating=5,
        expertise_rating=5,
        communication_rating=4,
        is_verified=False,
        is_anonymous=False
    )
    test_db.add(review)
    await test_db.commit()
    
    # Test endpoint
    response = await async_client.get(
        f"/api/v1/veterinarians/{veterinarian.id}/reviews",
        headers=headers
    )
    
    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["total"] == 1
    assert len(data["data"]["reviews"]) == 1
    
    review_data = data["data"]["reviews"][0]
    assert review_data["rating"] == 5
    assert review_data["title"] == "Excellent vet!"
    assert review_data["bedside_manner_rating"] == 5
    assert review_data["veterinarian_id"] == str(veterinarian.id)