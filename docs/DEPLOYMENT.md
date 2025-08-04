# Deployment Guide

This guide explains how database setup works in different environments and how to deploy the Veterinary Clinic Backend.

## 🔧 Development vs Production

### **Development Environment**
- **Tables**: Auto-created when app starts (if they don't exist)
- **Data**: Can be seeded with sample data
- **Migrations**: Optional (for testing migration workflows)

### **Production Environment**
- **Tables**: Created via Alembic migrations ONLY
- **Data**: No auto-seeding (manual data management)
- **Migrations**: Required and versioned

## 🏗️ Database Setup Strategies

### **Strategy 1: Development (Auto-Creation)**

```bash
# Method 1: One-command setup
./scripts/dev.sh

# Method 2: Manual setup
python scripts/init_db.py --seed
uvicorn app.main:app --reload
```

**What happens:**
1. ✅ App checks if tables exist
2. ✅ If not, creates them automatically
3. ✅ Starts FastAPI server
4. ✅ Ready for development

### **Strategy 2: Production (Migrations)**

```bash
# Method 1: Production deployment script
ENVIRONMENT=production ./scripts/deploy.sh

# Method 2: Manual production setup
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**What happens:**
1. ✅ Runs Alembic migrations to create/update tables
2. ✅ Validates database connection
3. ✅ Starts production server
4. ✅ No auto table creation

## 📊 Environment Behavior

| Environment | Table Creation | Sample Data | Migration Required |
|-------------|----------------|-------------|-------------------|
| `development` | ✅ Auto | ✅ Optional | ❌ No |
| `staging` | ❌ Manual | ❌ No | ✅ Yes |
| `production` | ❌ Manual | ❌ No | ✅ Yes |

## 🚀 Deployment Workflows

### **Local Development**

```bash
# Clone repository
git clone <repo-url>
cd vet-clinic-be

# Setup and start (one command)
./scripts/dev.sh
```

**Result**: http://localhost:8000 with sample data

### **Staging Deployment**

```bash
# Set environment
export ENVIRONMENT=staging
export DATABASE_URL="your-staging-db-url"
export JWT_SECRET_KEY="your-staging-jwt-secret"

# Deploy
./scripts/deploy.sh
```

### **Production Deployment**

```bash
# Set environment variables
export ENVIRONMENT=production
export DATABASE_URL="your-production-db-url"
export JWT_SECRET_KEY="your-production-jwt-secret"
export CLERK_SECRET_KEY="your-clerk-secret"

# Deploy
./scripts/deploy.sh
```

## 🔄 Migration Workflow

### **Creating Migrations**

```bash
# After changing models
alembic revision --autogenerate -m "Add new field to User model"

# Review the generated migration file
# Edit if necessary

# Apply migration
alembic upgrade head
```

### **Migration Commands**

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply all pending migrations
alembic upgrade head

# Apply specific migration
alembic upgrade <revision_id>

# Rollback one migration
alembic downgrade -1

# Show current migration status
alembic current

# Show migration history
alembic history
```

## 🐳 Docker Deployment

### **Dockerfile** (Coming Soon)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Run migrations and start server
CMD ["./scripts/deploy.sh"]
```

### **Docker Compose** (Coming Soon)

```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=${DATABASE_URL}
    depends_on:
      - db
  
  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=vetclinic
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
```

## ☁️ Cloud Deployment

### **Supabase + Vercel/Railway**

1. **Database**: Already configured with Supabase
2. **Migrations**: Run via deployment script
3. **Environment**: Set via platform environment variables

### **Environment Variables for Production**

```bash
# Required
ENVIRONMENT=production
DATABASE_URL=postgresql+asyncpg://...
JWT_SECRET_KEY=your-secure-secret
CLERK_SECRET_KEY=your-clerk-secret

# Optional
REDIS_URL=redis://...
SENTRY_DSN=https://...
ALLOWED_ORIGINS=https://yourdomain.com
```

## 🔍 Troubleshooting

### **Common Issues**

**"Table doesn't exist" in Production**
```bash
# Solution: Run migrations
alembic upgrade head
```

**"Auto table creation disabled"**
```bash
# This is correct behavior in production
# Use migrations instead:
alembic upgrade head
```

**Migration Conflicts**
```bash
# Check current status
alembic current

# Resolve conflicts manually
alembic merge <revision1> <revision2>
```

### **Health Checks**

```bash
# Test database connection
python scripts/test_db.py

# Check API health
curl http://localhost:8000/health

# Verify migrations
alembic current
```

## 📋 Deployment Checklist

### **Pre-Deployment**
- [ ] Environment variables configured
- [ ] Database accessible
- [ ] Migrations tested locally
- [ ] Dependencies updated

### **Deployment**
- [ ] Run `./scripts/deploy.sh`
- [ ] Verify health endpoint
- [ ] Test API endpoints
- [ ] Monitor logs

### **Post-Deployment**
- [ ] Database migrations applied
- [ ] API responding correctly
- [ ] Authentication working
- [ ] Monitoring configured

## 🔐 Security Considerations

### **Production Security**
- ✅ **No auto table creation** (prevents accidental schema changes)
- ✅ **Migration-based schema management** (versioned and auditable)
- ✅ **Environment-based configuration** (no hardcoded secrets)
- ✅ **Proper CORS configuration** (restricted origins)

### **Database Security**
- ✅ **Connection pooling** (prevents connection exhaustion)
- ✅ **SSL required** (encrypted connections)
- ✅ **Parameterized queries** (SQL injection prevention)
- ✅ **Access logging** (audit trail)

This deployment strategy ensures **safe production deployments** while maintaining **developer productivity** in local environments.