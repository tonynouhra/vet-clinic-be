# Veterinary Clinic Platform Backend

A comprehensive FastAPI-based backend for a veterinary clinic platform with features including pet management, appointment scheduling, communication, e-commerce, and more.

## Features

- **FastAPI** framework for high-performance REST API
- **PostgreSQL** database with **SQLAlchemy** ORM
- **Redis** for caching and session management
- **Celery** for background task processing
- **Clerk** integration for authentication
- **Docker** support for development and deployment
- **Alembic** for database migrations

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)

### Development Setup

1. **Clone and navigate to the backend directory:**
   ```bash
   cd vet-clinic-be
   ```

2. **Create environment file:**
   ```bash
   cp .env.example .env
   ```
   Update the `.env` file with your configuration values.

3. **Start with Docker Compose:**
   ```bash
   ./scripts/start.sh
   ```
   Or manually:
   ```bash
   docker-compose up --build
   ```

4. **The API will be available at:**
   - API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

### Local Development (without Docker)

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up database and Redis:**
   - Install PostgreSQL and Redis locally
   - Update `.env` with local connection strings

3. **Run database migrations:**
   ```bash
   alembic upgrade head
   ```

4. **Start the application:**
   ```bash
   uvicorn app.main:app --reload
   ```

5. **Start Celery worker (in another terminal):**
   ```bash
   celery -A app.core.celery_app worker --loglevel=info
   ```

## Project Structure

```
vet-clinic-be/
├── app/
│   ├── api/                 # API routes
│   │   └── v1/             # API version 1
│   ├── core/               # Core configuration
│   │   ├── config.py       # Settings management
│   │   ├── database.py     # Database configuration
│   │   ├── redis.py        # Redis client
│   │   ├── celery_app.py   # Celery configuration
│   │   └── exceptions.py   # Custom exceptions
│   ├── models/             # SQLAlchemy models
│   ├── schemas/            # Pydantic schemas
│   ├── tasks/              # Celery tasks
│   └── main.py            # FastAPI application
├── alembic/               # Database migrations
├── scripts/               # Utility scripts
├── docker-compose.yml     # Docker services
├── Dockerfile            # Container configuration
└── requirements.txt      # Python dependencies
```

## Environment Variables

Key environment variables (see `.env.example` for complete list):

- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `SECRET_KEY`: Application secret key
- `CLERK_SECRET_KEY`: Clerk authentication secret
- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_KEY`: Supabase API key

## Database Migrations

Create a new migration:
```bash
alembic revision --autogenerate -m "Description of changes"
```

Apply migrations:
```bash
alembic upgrade head
```

## Testing

Run tests:
```bash
pytest
```

Run tests with coverage:
```bash
pytest --cov=app
```

## API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/api/v1/openapi.json

## Background Tasks

The application uses Celery for background processing:

- **Notifications**: Email, SMS, and push notifications
- **Reports**: Generate various reports and analytics
- **Maintenance**: System cleanup and maintenance tasks

## Development

### Code Style

The project uses:
- **Black** for code formatting
- **isort** for import sorting
- **flake8** for linting

Format code:
```bash
black app/
isort app/
flake8 app/
```

### Adding New Features

1. Create models in `app/models/`
2. Create schemas in `app/schemas/`
3. Create API routes in `app/api/v1/`
4. Add background tasks in `app/tasks/`
5. Create database migrations with Alembic

## Deployment

The application is containerized and ready for deployment to various platforms:

- **Railway**
- **DigitalOcean**
- **AWS ECS**
- **Google Cloud Run**

## License

This project is licensed under the MIT License.