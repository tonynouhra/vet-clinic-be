# Veterinary Clinic Backend

A comprehensive REST API backend for veterinary clinic management built with FastAPI, featuring version-agnostic architecture and modern development practices.

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL database (Supabase)
- Redis (optional, for caching)

### 1. Clone and Setup
```bash
git clone <repository-url>
cd vet-clinic-be
```

### 2. Environment Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your actual values
nano .env
```

### 3. Start Development Server
```bash
# One-command setup and start
./scripts/dev.sh
```

This script will:
- Create virtual environment
- Install dependencies
- Initialize database
- Start FastAPI server

### 4. Access the API
- **API Server**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🏗️ Architecture

### Version-Agnostic Design
The backend uses a clean layered architecture where business logic is shared across all API versions:

```
📁 app/
├── 🔧 core/                    # Core configuration and database
├── 📊 models/                  # SQLAlchemy database models
├── 🎯 users/                   # Version-agnostic User resource
│   ├── controller.py           # Shared across ALL API versions
│   └── services.py             # Shared across ALL API versions
├── 🛠️ app_helpers/             # Shared utilities
│   ├── auth_helpers.py         # Authentication & authorization
│   ├── response_helpers.py     # Standardized responses
│   ├── validation_helpers.py   # Common validation
│   └── dependency_helpers.py   # Dependency injection
└── 🌐 api/                     # Version-specific routes & schemas
    ├── schemas/v1/             # V1 request/response models
    ├── schemas/v2/             # V2 request/response models
    ├── v1/                     # V1 API endpoints
    └── v2/                     # V2 API endpoints
```

### Key Benefits
- ✅ **Single Source of Truth**: Business logic shared across all versions
- ✅ **Easy Version Addition**: Add V3, V4+ without touching business logic
- ✅ **No Code Duplication**: Controllers and services work with any version
- ✅ **Future-Proof**: Dynamic parameter handling for new versions

## 🛠️ Development Scripts

### Database Management
```bash
# Initialize database with tables
python scripts/init_db.py

# Initialize with sample data
python scripts/init_db.py --seed

# Test database connection
python scripts/test_db.py
```

### Development Server
```bash
# Start development server (auto-setup)
./scripts/dev.sh

# Manual server start
uvicorn app.main:app --reload
```

## 📊 Database

### Connection
- **Provider**: Supabase PostgreSQL
- **Connection**: Configured via `DATABASE_URL` environment variable
- **Features**: Connection pooling, async operations, health checks

### Models
- **User**: Authentication, roles, profile management
- **Pet**: Pet profiles and health records (coming soon)
- **Appointment**: Scheduling and management (coming soon)
- **Clinic**: Veterinarian and clinic data (coming soon)

### Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## 🔐 Authentication

### Clerk Integration
- JWT token validation
- Role-based access control
- User session management

### Roles
- `admin`: Full system access
- `veterinarian`: Medical records and appointments
- `receptionist`: Appointments and basic user management
- `clinic_manager`: Clinic operations and staff management
- `pet_owner`: Personal pets and appointments

## 🧪 Testing

### Run Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_users.py
```

### Test Database
```bash
# Test database connectivity
python scripts/test_db.py
```

## 📝 API Documentation

### Interactive Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### API Versions
- **V1**: `/api/v1/` - Basic functionality
- **V2**: `/api/v2/` - Enhanced features (coming soon)

### Response Format
```json
{
  "success": true,
  "message": "Operation successful",
  "data": {...},
  "meta": {
    "pagination": {...}
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## 🔧 Configuration

### Environment Variables
All configuration is handled through environment variables. See `.env.example` for required variables:

- `DATABASE_URL`: PostgreSQL connection string
- `CLERK_SECRET_KEY`: Clerk authentication secret
- `JWT_SECRET_KEY`: JWT signing secret
- `SUPABASE_*`: File storage configuration
- `REDIS_URL`: Redis connection for caching

### Settings
Configuration is managed through Pydantic Settings in `app/core/config.py`.

## 📁 Project Structure

```
vet-clinic-be/
├── 📁 app/                     # Main application
│   ├── 🔧 core/               # Core configuration
│   ├── 📊 models/             # Database models
│   ├── 👥 users/              # User resource (version-agnostic)
│   ├── 🛠️ app_helpers/        # Shared utilities
│   └── 🌐 api/                # API routes and schemas
├── 📁 scripts/                # Development scripts
│   ├── init_db.py            # Database initialization
│   ├── test_db.py            # Database testing
│   └── dev.sh                # Development server
├── 📁 alembic/                # Database migrations
├── 📁 tests/                  # Test suite
├── 📄 requirements.txt        # Python dependencies
├── 📄 .env.example           # Environment template
└── 📄 README.md              # This file
```

## 🚀 Deployment

### Docker (Coming Soon)
```bash
# Build image
docker build -t vet-clinic-be .

# Run container
docker run -p 8000:8000 vet-clinic-be
```

### Production Checklist
- [ ] Set `ENVIRONMENT=production`
- [ ] Configure production database
- [ ] Set secure `JWT_SECRET_KEY`
- [ ] Configure CORS origins
- [ ] Set up monitoring (Sentry)
- [ ] Configure email settings

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open Pull Request

### Development Guidelines
- Follow the version-agnostic architecture patterns
- Write tests for new features
- Update documentation
- Use type hints
- Follow PEP 8 style guide

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

### Common Issues

**Database Connection Failed**
```bash
# Check your .env configuration
python scripts/test_db.py

# Reinitialize database
python scripts/init_db.py --seed
```

**Import Errors**
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # or .venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Getting Help
- Check the [API Documentation](http://localhost:8000/docs)
- Review the [Architecture Guide](docs/API_VERSIONING_GUIDE.md)
- Run database tests: `python scripts/test_db.py`

---

Built with ❤️ using FastAPI, SQLAlchemy, and modern Python practices.