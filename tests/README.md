# Testing Documentation

This directory contains all tests for the vet-clinic-be project.

## Structure

```
tests/
├── unit/                           # Unit tests
│   ├── test_models/               # Database model tests
│   │   └── test_all_models.py    # Comprehensive model validation
│   ├── test_services/            # Business logic tests
│   └── test_schemas/             # Pydantic schema tests
├── integration/                   # Integration tests
└── fixtures/                     # Test data and fixtures
```

## Running Tests

### Run All Model Tests
```bash
# Activate virtual environment
source .venv/bin/activate

# Run model tests
python -m pytest tests/unit/test_models/ -v

# Or run the comprehensive model test directly
python tests/unit/test_models/test_all_models.py
```

### Run All Tests
```bash
python -m pytest tests/ -v
```

## Test Categories

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test component interactions
- **Model Tests**: Validate database models and relationships
- **Service Tests**: Test business logic and services
- **Schema Tests**: Validate API request/response schemas