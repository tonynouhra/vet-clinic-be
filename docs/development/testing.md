# Testing Guide

This document provides comprehensive guidelines for testing the vet-clinic-be project.

## Testing Structure

```
tests/
├── unit/                           # Unit tests
│   ├── test_models/               # Database model tests
│   │   └── test_all_models.py    # Comprehensive model validation
│   ├── test_services/            # Business logic tests
│   └── test_schemas/             # Pydantic schema tests
├── integration/                   # Integration tests
│   ├── test_api/                 # API endpoint tests
│   ├── test_database/            # Database integration tests
│   └── test_tasks/               # Background task tests
└── fixtures/                     # Test data and fixtures
```

## Running Tests

### Prerequisites

```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Model Tests

```bash
# Run comprehensive model tests
python tests/unit/test_models/test_all_models.py

# Run with pytest (when available)
python -m pytest tests/unit/test_models/ -v
```

### All Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=app --cov-report=html
```

## Task Verification

Use verification scripts to ensure task completion:

```bash
# Verify Task 2 completion
python scripts/verify_tasks/verify_task_2.py
```

## Test Categories

### Unit Tests
- **Model Tests**: Validate database models and relationships
- **Service Tests**: Test business logic in isolation
- **Schema Tests**: Validate Pydantic schemas

### Integration Tests
- **API Tests**: End-to-end API testing
- **Database Tests**: Database operations and migrations
- **Task Tests**: Background task execution

## Writing Tests

### Model Tests
```python
def test_user_model():
    user = User(
        clerk_id="test_123",
        email="test@example.com",
        first_name="Test",
        last_name="User"
    )
    assert user.full_name == "Test User"
```

### API Tests
```python
async def test_create_user_endpoint(test_client):
    response = await test_client.post("/api/v1/users", json={
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User"
    })
    assert response.status_code == 201
```

## Best Practices

1. **Test Isolation**: Each test should be independent
2. **Clear Naming**: Use descriptive test names
3. **Arrange-Act-Assert**: Follow the AAA pattern
4. **Mock External Dependencies**: Use mocks for external services
5. **Test Edge Cases**: Include boundary and error conditions