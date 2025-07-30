# API Documentation

This directory contains comprehensive API documentation for the vet-clinic-be REST API.

## API Overview

The Veterinary Clinic Backend provides a RESTful API built with FastAPI, offering comprehensive endpoints for:

- **User Management**: Authentication, profiles, and role-based access
- **Pet Management**: Pet profiles, health records, and medical history
- **Appointment Scheduling**: Booking, availability, and appointment lifecycle
- **Clinic Management**: Clinic information, veterinarian profiles, and reviews
- **Communication**: Real-time messaging and AI chatbot integration
- **Emergency Services**: Urgent care requests and provider matching

## Base URL

```
Development: http://localhost:8000
Production: https://api.vetclinic.com
```

## API Versioning

All API endpoints are versioned and prefixed with `/api/v1/`:

```
/api/v1/users
/api/v1/pets
/api/v1/appointments
/api/v1/clinics
/api/v1/chat
```

## Authentication

The API uses JWT tokens provided by Clerk for authentication:

```http
Authorization: Bearer <jwt_token>
```

## Response Format

All API responses follow a consistent JSON format:

### Success Response
```json
{
  "data": {
    // Response data
  },
  "meta": {
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "req_123456789"
  }
}
```

### Error Response
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

## Documentation Files

- [**endpoints.md**](./endpoints.md) - Complete API endpoint reference
- [**authentication.md**](./authentication.md) - Authentication and authorization guide
- [**schemas.md**](./schemas.md) - Request/response schema definitions

## Interactive Documentation

When running the development server, interactive API documentation is available at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Rate Limiting

API endpoints are rate-limited based on user roles:

- **Anonymous**: 100 requests/hour
- **Pet Owner**: 1000 requests/hour
- **Veterinarian**: 5000 requests/hour
- **Clinic Admin**: 10000 requests/hour

## Status Codes

The API uses standard HTTP status codes:

- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `422` - Validation Error
- `500` - Internal Server Error