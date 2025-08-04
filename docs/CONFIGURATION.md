# Configuration Guide

This guide explains how to properly configure the Veterinary Clinic Backend with all required environment variables.

## 🔧 Configuration Overview

The application uses **environment variables** for configuration, loaded from a `.env` file. All settings are validated on startup to prevent runtime errors.

## 📋 Required Configuration

### **Critical Settings** (Must be configured)

#### **DATABASE_URL** 🗄️
```bash
DATABASE_URL=postgresql+asyncpg://postgres.vqmpkxadwsbcmclzulsd:X1554lQ2kXl82egQ@aws-0-eu-north-1.pooler.supabase.com:6543/postgres?sslmode=require
```
- **Description**: PostgreSQL database connection string
- **Format**: `postgresql+asyncpg://user:password@host:port/database?sslmode=require`
- **Critical**: ✅ Yes - App won't start without this

#### **DEBUG** 🐛
```bash
DEBUG=true
```
- **Description**: Enable debug mode for development
- **Values**: `true` or `false`
- **Critical**: ✅ Yes - Controls logging and error handling

#### **ENVIRONMENT** 🌍
```bash
ENVIRONMENT=development
```
- **Description**: Application environment
- **Values**: `development`, `staging`, `production`
- **Critical**: ✅ Yes - Controls auto table creation and other behaviors

#### **JWT_SECRET_KEY** 🔐
```bash
JWT_SECRET_KEY=your-secure-secret-key-change-in-production
```
- **Description**: Secret key for JWT token signing
- **Critical**: ✅ Yes - Required for authentication
- **Security**: Use a strong, random key in production

### **Important Settings** (Recommended)

#### **Database Pool Settings**
```bash
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
```
- **Description**: Database connection pool configuration
- **Default**: 10 connections, 20 overflow

#### **Redis Configuration**
```bash
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```
- **Description**: Redis for caching and Celery message broker
- **Required for**: Background tasks, caching, rate limiting

#### **Authentication (Clerk)**
```bash
CLERK_SECRET_KEY=your-clerk-secret-key
CLERK_PUBLISHABLE_KEY=your-clerk-publishable-key
```
- **Description**: Clerk authentication service keys
- **Required for**: User authentication and management

#### **File Storage (Supabase)**
```bash
SUPABASE_STORAGE_ENDPOINT=https://vqmpkxadwsbcmclzulsd.storage.supabase.co/storage/v1/s3
SUPABASE_STORAGE_BUCKET=vetcclinix-files
SUPABASE_ACCESS_KEY_ID=8b0dc9f8aa7833337e1da9d66dbd93cf
SUPABASE_SECRET_ACCESS_KEY=7c8796e12609f994660545b31da93cf44e466ef4c6d08b17189b5f2df583068d
```
- **Description**: Supabase storage for file uploads
- **Required for**: Pet photos, documents, media files

#### **CORS and Security**
```bash
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001
RATE_LIMIT_PER_MINUTE=60
```
- **Description**: CORS origins and API rate limiting
- **Format**: Comma-separated list for origins

#### **Logging**
```bash
LOG_LEVEL=INFO
SENTRY_DSN=your-sentry-dsn-url
```
- **Description**: Logging level and error tracking
- **Values**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

## 🛠️ Configuration Setup

### **Method 1: Automatic Verification** ⭐ **Recommended**
```bash
# Run comprehensive configuration check
python scripts/verify_config.py
```

**What it checks:**
- ✅ All required variables are set
- ✅ Values are in correct format
- ✅ Database connection works
- ✅ Configuration loads successfully

### **Method 2: Generate Template**
```bash
# Generate .env template with all variables
python scripts/verify_config.py --template

# Copy and customize
cp .env.template .env
nano .env
```

### **Method 3: Manual Setup**
```bash
# Copy example file
cp .env.example .env

# Edit with your values
nano .env
```

## 🔍 Configuration Validation

### **Startup Validation**
The application automatically validates configuration on startup:

```bash
# When you start the app
uvicorn app.main:app --reload
```

**Startup log:**
```
🚀 Starting Veterinary Clinic Backend
Environment: development
Debug Mode: True
🔍 Verifying configuration...
✅ Configuration verified successfully
```

### **Manual Validation**
```bash
# Check configuration anytime
python scripts/verify_config.py

# Run all startup checks
python scripts/startup_check.py
```

## ⚠️ Common Configuration Issues

### **Issue 1: Missing .env File**
```
❌ .env file not found!
```

**Solution:**
```bash
cp .env.example .env
# Edit .env with your values
```

### **Issue 2: Invalid Database URL**
```
❌ DATABASE_URL: Should start with 'postgresql://' or 'postgresql+asyncpg://'
```

**Solution:**
```bash
# Correct format
DATABASE_URL=postgresql+asyncpg://user:password@host:port/database
```

### **Issue 3: Missing Critical Variables**
```
❌ JWT_SECRET_KEY: Missing from .env file
```

**Solution:**
```bash
# Add to .env file
JWT_SECRET_KEY=your-secure-secret-key
```

### **Issue 4: Invalid Environment Value**
```
❌ ENVIRONMENT: Invalid value 'dev'. Valid values: development, staging, production
```

**Solution:**
```bash
# Use exact values
ENVIRONMENT=development
```

## 🏭 Environment-Specific Configuration

### **Development**
```bash
DEBUG=true
ENVIRONMENT=development
LOG_LEVEL=DEBUG
# Database auto-creates tables
# Detailed error messages
```

### **Staging**
```bash
DEBUG=false
ENVIRONMENT=staging
LOG_LEVEL=INFO
# Uses Alembic migrations
# Production-like settings
```

### **Production**
```bash
DEBUG=false
ENVIRONMENT=production
LOG_LEVEL=WARNING
SENTRY_DSN=your-sentry-dsn
# Strict security settings
# No auto table creation
```

## 🔐 Security Best Practices

### **Secrets Management**
- ✅ **Never commit** `.env` files to version control
- ✅ **Use strong secrets** for JWT_SECRET_KEY
- ✅ **Rotate secrets** regularly in production
- ✅ **Use environment variables** in deployment platforms

### **Database Security**
- ✅ **Use SSL connections** (`sslmode=require`)
- ✅ **Limit database user permissions**
- ✅ **Use connection pooling**
- ✅ **Monitor connection usage**

### **API Security**
- ✅ **Set appropriate CORS origins**
- ✅ **Configure rate limiting**
- ✅ **Use HTTPS in production**
- ✅ **Enable request logging**

## 🧪 Testing Configuration

### **Test Database Connection**
```bash
python scripts/test_db.py
```

### **Test Configuration Loading**
```bash
python -c "from app.core.config import get_settings; print(get_settings().ENVIRONMENT)"
```

### **Test Full Application**
```bash
python scripts/startup_check.py
```

## 📊 Configuration Checklist

### **Before First Run:**
- [ ] `.env` file exists
- [ ] All critical variables set
- [ ] Database URL is correct
- [ ] JWT secret is secure
- [ ] Environment is set correctly

### **Before Production:**
- [ ] DEBUG=false
- [ ] Strong JWT secret
- [ ] Production database URL
- [ ] CORS origins configured
- [ ] Sentry DSN configured
- [ ] SSL certificates ready

### **Verification Commands:**
```bash
# Quick check
python scripts/verify_config.py

# Comprehensive check
python scripts/startup_check.py

# Database test
python scripts/test_db.py

# PyCharm setup
python scripts/setup_pycharm.py
```

## 🚀 Quick Start

1. **Copy configuration:**
   ```bash
   cp .env.example .env
   ```

2. **Update critical settings:**
   ```bash
   nano .env
   # Set DATABASE_URL, JWT_SECRET_KEY, etc.
   ```

3. **Verify configuration:**
   ```bash
   python scripts/verify_config.py
   ```

4. **Start application:**
   ```bash
   ./scripts/dev.sh
   ```

Your configuration is now properly set up and validated! 🎉