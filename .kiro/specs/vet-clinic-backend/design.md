# Backend Design Document

## Overview

The Veterinary Clinic Backend (vet-clinic-be) is designed as a unified, high-performance REST API service built with FastAPI and Python 3.11+. The backend follows a clean architecture pattern with clear separation of concerns, providing comprehensive APIs for pet health management, appointment scheduling, communication, e-commerce, and administrative functions. The system is designed for scalability, maintainability, and security, serving as the single source of truth for all veterinary clinic platform data and business logic.

## Architecture

### System Architecture

The backend follows a clean layered architecture pattern with proper separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                     │
│              Thin routing and dependency injection         │
├─────────────────────────────────────────────────────────────┤
│                   Controller Layer                         │
│           HTTP handling and business logic orchestration   │
├─────────────────────────────────────────────────────────────┤
│                   Service Layer                            │
│              Data access and core business logic           │
├─────────────────────────────────────────────────────────────┤
│                   Database Layer                           │
│                SQLAlchemy models and queries               │
└─────────────────────────────────────────────────────────────┘
```

### Layered Architecture Pattern with API Versioning

#### API Layer (api/v1/, api/v2/) - VERSION SPECIFIC
- **Purpose**: Version-specific route definition and HTTP method handling
- **Responsibilities**:
  - Define version-specific FastAPI routes and HTTP methods
  - Handle dependency injection (database sessions, authentication)
  - Use version-specific schemas for request/response validation
  - Delegate immediately to shared, version-agnostic controllers
  - Maintain RESTful URL patterns within each version

#### Controller Layer (resource packages/) - VERSION AGNOSTIC
- **Purpose**: HTTP request processing and business logic orchestration shared across all API versions
- **Responsibilities**:
  - Handle HTTP request/response processing for any API version
  - Accept parameters from any API version gracefully
  - Implement business logic workflows
  - Coordinate multiple service calls
  - Handle authentication and authorization
  - Format responses using response helpers
  - Apply business rules and validation
  - Manage transaction boundaries

#### Service Layer (services.py in each resource/) - VERSION AGNOSTIC
- **Purpose**: Data access and core business logic shared across all API versions
- **Responsibilities**:
  - Handle database operations
  - Implement core business logic
  - Manage entity lifecycle
  - Handle external API integrations
  - Provide data transformation
  - Execute database queries and transactions

### Technology Stack

#### Core Technologies
- **API Framework**: FastAPI 0.104+ for high-performance async REST API development
- **Programming Language**: Python 3.11+ with type hints and async/await support
- **Data Validation**: Pydantic v2 for request/response validation and serialization
- **Database**: PostgreSQL 15+ hosted on Supabase for reliability and managed services
- **ORM**: SQLAlchemy 2.0 with async support for database operations
- **Cache Layer**: Redis 7+ for session management, rate limiting, and caching
- **Background Processing**: Celery 5.3+ with Redis as message broker for async tasks

#### Authentication & Security
- **Authentication**: Clerk integration with JWT token validation
- **Authorization**: Role-based access control (RBAC) with custom decorators
- **Security**: CORS configuration, rate limiting, input validation, and security headers

#### File Storage & Media
- **File Storage**: Supabase Storage for images, documents, and media files
- **Image Processing**: Pillow for image optimization and resizing
- **File Validation**: Custom validators for file types, sizes, and security

#### Monitoring & Observability
- **Error Tracking**: Sentry for error monitoring and performance tracking
- **Logging**: Structured logging with correlation IDs using Python logging
- **Health Checks**: Custom health check endpoints for system monitoring

## Components and Interfaces

### Project Structure

```
vet-clinic-be/
├── app/                          # Main application package
│   ├── __init__.py
│   ├── main.py                   # FastAPI application entry point
│   ├── core/                     # Core utilities and configuration
│   │   ├── __init__.py
│   │   ├── config.py            # Pydantic settings and environment config
│   │   ├── database.py          # Database connection and session management
│   │   ├── security.py          # Authentication and authorization utilities
│   │   ├── exceptions.py        # Custom exception classes and handlers
│   │   ├── celery_app.py        # Celery configuration and setup
│   │   └── redis.py             # Redis connection and utilities
│   ├── models/                   # SQLAlchemy database models
│   │   ├── __init__.py
│   │   ├── user.py              # User, roles, and authentication models
│   │   ├── pet.py               # Pet profiles and health records
│   │   ├── appointment.py       # Appointment scheduling models
│   │   ├── clinic.py            # Clinic and veterinarian models
│   │   └── communication.py     # Chat and messaging models
│   ├── api/                      # API route handlers with versioning
│   │   ├── __init__.py
│   │   ├── deps.py              # API dependencies and middleware
│   │   ├── schemas/             # Version-specific schemas
│   │   │   ├── __init__.py
│   │   │   ├── v1/              # V1 request/response models
│   │   │   │   ├── __init__.py
│   │   │   │   ├── users.py     # V1 user schemas
│   │   │   │   ├── pets.py      # V1 pet schemas
│   │   │   │   ├── appointments.py # V1 appointment schemas
│   │   │   │   ├── clinics.py   # V1 clinic schemas
│   │   │   │   └── chat.py      # V1 chat schemas
│   │   │   └── v2/              # V2 request/response models (future)
│   │   │       ├── __init__.py
│   │   │       ├── users.py     # V2 enhanced user schemas
│   │   │       ├── pets.py      # V2 enhanced pet schemas
│   │   │       └── [other v2 schemas]
│   │   ├── v1/                  # API version 1 routes
│   │   │   ├── __init__.py
│   │   │   ├── users.py         # V1 user endpoints → shared controllers
│   │   │   ├── pets.py          # V1 pet endpoints → shared controllers
│   │   │   ├── appointments.py  # V1 appointment endpoints → shared controllers
│   │   │   ├── clinics.py       # V1 clinic endpoints → shared controllers
│   │   │   ├── chat.py          # V1 chat endpoints → shared controllers
│   │   │   └── emergency.py     # V1 emergency endpoints → shared controllers
│   │   └── v2/                  # API version 2 routes (future)
│   │       ├── __init__.py
│   │       ├── users.py         # V2 user endpoints → same shared controllers
│   │       ├── pets.py          # V2 pet endpoints → same shared controllers
│   │       └── [other v2 endpoints]
│   ├── users/                    # Version-agnostic User resource package
│   │   ├── __init__.py
│   │   ├── controller.py        # Shared across ALL API versions
│   │   └── services.py          # Shared across ALL API versions
│   ├── pets/                     # Version-agnostic Pet resource package
│   │   ├── __init__.py
│   │   ├── controller.py        # Shared across ALL API versions
│   │   └── services.py          # Shared across ALL API versions
│   ├── appointments/             # Version-agnostic Appointment resource package
│   │   ├── __init__.py
│   │   ├── controller.py        # Shared across ALL API versions
│   │   └── services.py          # Shared across ALL API versions
│   ├── clinics/                  # Version-agnostic Clinic resource package
│   │   ├── __init__.py
│   │   ├── controller.py        # Shared across ALL API versions
│   │   └── services.py          # Shared across ALL API versions
│   ├── chat/                     # Version-agnostic Communication resource package
│   │   ├── __init__.py
│   │   ├── controller.py        # Shared across ALL API versions
│   │   └── services.py          # Shared across ALL API versions
│   ├── app_helpers/              # Common functionality and utilities
│   │   ├── __init__.py
│   │   ├── auth_helpers.py      # Authentication utilities
│   │   ├── response_helpers.py  # Response formatting utilities
│   │   ├── validation_helpers.py # Common validation utilities
│   │   └── dependency_helpers.py # Dependency injection utilities
│   ├── services/                 # Legacy business logic services (to be migrated)
│   │   ├── __init__.py
│   │   ├── notification_service.py # Email/SMS/Push notifications
│   │   ├── payment_service.py   # Payment processing integration
│   │   ├── location_service.py  # Location-based services
│   │   ├── ai_service.py        # AI chatbot integration
│   │   └── [other service files]
│   ├── tasks/                    # Celery background tasks
│   │   ├── __init__.py
│   │   ├── notification_tasks.py # Reminder and notification tasks
│   │   ├── report_tasks.py      # Report generation tasks
│   │   ├── maintenance_tasks.py # System maintenance tasks
│   │   └── [other task files]
│   └── utils/                    # Utility functions
│       ├── __init__.py
│       ├── email.py             # Email utilities and templates
│       ├── file_storage.py      # File upload/download utilities
│       ├── validators.py        # Custom validation functions
│       └── [other utility files]
├── app_tests/                    # Test suite (aligned with api-architecture-restructure)
│   ├── __init__.py
│   ├── README.md                # Testing documentation
│   ├── conftest.py              # Pytest configuration and fixtures
│   ├── unit/                    # Unit tests for individual functions
│   │   ├── __init__.py
│   │   ├── test_controllers/    # Controller unit tests
│   │   ├── test_services/       # Service unit tests
│   │   ├── test_models/         # Database model tests
│   │   │   ├── __init__.py
│   │   │   └── test_all_models.py # Comprehensive model validation
│   │   └── test_schemas/        # Pydantic schema tests
│   ├── functional/              # Functional tests for complete workflows
│   │   ├── __init__.py
│   │   ├── test_user_workflows/
│   │   ├── test_pet_workflows/
│   │   └── test_appointment_workflows/
│   ├── integration/             # Integration tests for full API flows
│   │   ├── __init__.py
│   │   ├── test_v1_endpoints/   # V1 API integration tests
│   │   ├── test_v2_endpoints/   # V2 API integration tests (future)
│   │   ├── test_version_compatibility/ # Cross-version compatibility tests
│   │   ├── test_database/       # Database integration tests
│   │   └── test_tasks/          # Background task tests
│   └── fixtures/                # Test data and fixtures
├── scripts/                     # Development and utility scripts
│   ├── dev.sh                  # Development server script
│   ├── start.sh                # Production start script
│   └── verify_tasks/           # Task verification scripts
│       ├── __init__.py
│       ├── README.md           # Verification documentation
│       └── verify_task_2.py    # Task 2 completion verification
├── docs/                       # Project documentation
│   ├── README.md              # Documentation overview
│   ├── api/                   # API documentation
│   │   ├── endpoints.md       # API endpoint documentation
│   │   ├── authentication.md  # Authentication and authorization
│   │   └── schemas.md         # Request/response schemas
│   ├── development/           # Development guides
│   │   ├── setup.md          # Development environment setup
│   │   ├── testing.md        # Testing guidelines and practices
│   │   ├── database.md       # Database setup and migrations
│   │   └── contributing.md   # Contribution guidelines
│   ├── deployment/           # Deployment documentation
│   │   ├── docker.md         # Docker deployment guide
│   │   ├── production.md     # Production deployment
│   │   └── monitoring.md     # Monitoring and logging
│   └── architecture/         # System architecture
│       ├── overview.md       # System architecture overview
│       ├── database.md       # Database design and schema
│       └── services.md       # Service layer architecture
├── alembic/                  # Database migrations
│   ├── versions/             # Migration version files
│   ├── env.py               # Alembic environment configuration
│   └── script.py.mako       # Migration script template
├── docker-compose.yml       # Local development environment
├── Dockerfile               # Container configuration
├── requirements.txt         # Python dependencies
├── alembic.ini             # Alembic configuration
├── test_setup.py           # Setup verification script
└── .env.example            # Environment variables template
```

### API Design Patterns

#### RESTful API Structure
All APIs follow RESTful conventions with consistent URL patterns:

```
/api/v1/{resource}                # Collection operations (GET, POST)
/api/v1/{resource}/{id}           # Individual resource operations (GET, PUT, DELETE)
/api/v1/{resource}/{id}/{sub}     # Sub-resource operations
```

#### Request/Response Format
- **Content Type**: `application/json` for all requests and responses
- **Authentication**: Bearer token in Authorization header
- **Pagination**: Cursor-based pagination for large datasets
- **Filtering**: Query parameters for filtering and sorting

#### Error Response Format
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": {
      "field": "email",
      "issue": "Invalid email format"
    },
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "req_123456789"
  }
}
```

### Database Design

#### Core Entity Relationships

```mermaid
erDiagram
    User ||--o{ Pet : owns
    User ||--o{ Appointment : books
    User ||--o{ Order : places
    User ||--o{ Conversation : participates
    Pet ||--o{ Appointment : has
    Pet ||--o{ HealthRecord : has
    Pet ||--o{ Reminder : has
    Veterinarian ||--o{ Appointment : attends
    Veterinarian }|--|| User : is
    Clinic ||--o{ Veterinarian : employs
    Clinic ||--o{ Appointment : hosts
    Conversation ||--o{ Message : contains
    Product ||--o{ OrderItem : included_in
    Order ||--o{ OrderItem : contains
    
    User {
        uuid id PK
        string email UK
        string clerk_id UK
        string first_name
        string last_name
        enum role
        json preferences
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }
    
    Pet {
        uuid id PK
        uuid owner_id FK
        string name
        string breed
        string species
        date birth_date
        enum gender
        float weight
        text medical_notes
        json metadata
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }
    
    Appointment {
        uuid id PK
        uuid pet_id FK
        uuid veterinarian_id FK
        uuid clinic_id FK
        datetime scheduled_at
        integer duration_minutes
        enum status
        enum service_type
        decimal price
        text notes
        json metadata
        timestamp created_at
        timestamp updated_at
    }
    
    HealthRecord {
        uuid id PK
        uuid pet_id FK
        enum record_type
        string title
        text description
        date record_date
        json metadata
        string file_url
        timestamp created_at
    }
```

#### Database Schema Optimization

**Indexing Strategy:**
- Primary keys: UUID with B-tree indexes
- Foreign keys: B-tree indexes for join optimization
- Search fields: GIN indexes for full-text search
- Timestamp fields: B-tree indexes for date range queries
- Location fields: GiST indexes for geographic queries

**Performance Considerations:**
- Connection pooling with SQLAlchemy async engine
- Query optimization with eager loading for relationships
- Database-level constraints for data integrity
- Partitioning for large tables (appointments, messages)

## Service Layer Architecture

### Authentication Service
- **Clerk Integration**: JWT token validation and user session management
- **Role Management**: RBAC implementation with permission checking
- **Session Handling**: Redis-based session storage and management

### Notification Service
- **Email Notifications**: Template-based email sending with SMTP
- **SMS Notifications**: Integration with SMS providers for urgent alerts
- **Push Notifications**: Mobile push notification handling
- **Notification Preferences**: User-configurable notification settings

### Appointment Service
- **Availability Management**: Real-time availability checking and conflict resolution
- **Booking Logic**: Complex booking rules and validation
- **Reminder System**: Automated reminder scheduling and delivery
- **Calendar Integration**: Calendar view data generation and management

### Payment Service
- **Payment Processing**: Secure payment handling with multiple providers
- **Subscription Management**: Recurring payment and subscription lifecycle
- **Invoice Generation**: Automated invoice and receipt generation
- **Refund Processing**: Refund handling and transaction management

### Location Service
- **Geographic Search**: Proximity-based service discovery
- **Distance Calculation**: Haversine formula for distance calculations
- **Map Integration**: Geographic coordinate management
- **Emergency Routing**: Priority-based emergency service routing

## Background Task Processing

### Celery Configuration
```python
# Celery settings
broker_url = "redis://localhost:6379/0"
result_backend = "redis://localhost:6379/0"
task_serializer = "json"
accept_content = ["json"]
result_serializer = "json"
timezone = "UTC"
enable_utc = True
```

### Task Categories

#### Notification Tasks
- **Appointment Reminders**: Scheduled reminder notifications
- **Health Record Alerts**: Vaccination and medication reminders
- **Emergency Notifications**: Real-time emergency alert distribution
- **Marketing Communications**: Newsletter and promotional emails

#### Data Processing Tasks
- **Report Generation**: Asynchronous report creation and delivery
- **Data Export**: Large dataset export and file generation
- **Image Processing**: Photo optimization and thumbnail generation
- **Data Cleanup**: Automated data archival and cleanup

#### System Maintenance Tasks
- **Database Optimization**: Index maintenance and query optimization
- **File Cleanup**: Unused file removal and storage optimization
- **Cache Management**: Cache invalidation and refresh operations
- **Health Monitoring**: System health checks and alerting

## Security Architecture

### Authentication & Authorization
- **JWT Tokens**: Stateless authentication with Clerk integration
- **Role-Based Access**: Granular permission system with role inheritance
- **API Key Management**: Third-party integration authentication
- **Session Security**: Secure session handling with Redis

### Data Protection
- **Input Validation**: Comprehensive request validation with Pydantic
- **SQL Injection Prevention**: Parameterized queries with SQLAlchemy
- **XSS Protection**: Output encoding and sanitization
- **CSRF Protection**: CSRF token validation for state-changing operations

### API Security
- **Rate Limiting**: Redis-based rate limiting per user and endpoint
- **CORS Configuration**: Proper cross-origin resource sharing setup
- **Security Headers**: Comprehensive security header implementation
- **Request Logging**: Audit logging for sensitive operations

## Error Handling Strategy

### Exception Hierarchy
```python
class VetClinicException(Exception):
    """Base exception for vet clinic application"""
    pass

class ValidationError(VetClinicException):
    """Data validation errors"""
    pass

class AuthenticationError(VetClinicException):
    """Authentication and authorization errors"""
    pass

class BusinessLogicError(VetClinicException):
    """Business rule violations"""
    pass
```

### Error Response Handling
- **Structured Errors**: Consistent error response format
- **Error Codes**: Standardized error codes for client handling
- **Logging Integration**: Comprehensive error logging with context
- **User-Friendly Messages**: Appropriate error messages for different audiences

## Testing Strategy

### Unit Testing
- **Model Testing**: SQLAlchemy model validation and relationship testing
- **Service Testing**: Business logic testing with mocked dependencies
- **Schema Testing**: Pydantic schema validation and serialization testing
- **Utility Testing**: Helper function and utility testing

### Integration Testing
- **API Testing**: End-to-end API endpoint testing with test database
- **Database Testing**: Database operation and migration testing
- **Authentication Testing**: Clerk integration and JWT handling testing
- **Background Task Testing**: Celery task execution and reliability testing

### Performance Testing
- **Load Testing**: API endpoint performance under load
- **Database Performance**: Query optimization and indexing validation
- **Cache Performance**: Redis caching effectiveness testing
- **Memory Profiling**: Memory usage and leak detection

### Test Infrastructure
```python
# pytest configuration
pytest_plugins = [
    "pytest_asyncio",
    "pytest_mock",
    "pytest_cov"
]

# Test database setup
TEST_DATABASE_URL = "postgresql://test:test@localhost/test_vetclinic"

# Test fixtures
@pytest.fixture
async def test_db():
    # Database setup and teardown
    pass

@pytest.fixture
def test_client():
    # FastAPI test client setup
    pass
```

## Deployment Architecture

### Containerization
- **Docker Configuration**: Multi-stage Docker builds for optimization
- **Environment Management**: Environment-specific configuration handling
- **Health Checks**: Container health check implementation
- **Resource Limits**: Proper resource allocation and limits

### Production Considerations
- **Database Migrations**: Automated migration deployment with rollback capability
- **Environment Variables**: Secure environment variable management
- **Logging Configuration**: Production-ready logging setup
- **Monitoring Integration**: Comprehensive monitoring and alerting setup

This design provides a robust, scalable, and maintainable backend architecture that can handle the complex requirements of a veterinary clinic platform while ensuring security, performance, and reliability.