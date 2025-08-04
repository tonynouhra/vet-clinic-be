# Database Management Guide

This guide explains how database tables are managed in different scenarios and environments.

## 🧠 Smart Table Management

### **Key Principle: Tables are NEVER dropped unless explicitly requested**

The system uses **smart table creation** that:
- ✅ **Only creates tables that don't exist**
- ✅ **Never drops existing tables** (unless `--force` flag)
- ✅ **Preserves all your data**
- ✅ **Automatically detects new tables** when you add models

## 📊 How It Works

### **Development Environment**

#### **First Time Setup**
```bash
./scripts/dev.sh
```

**What happens:**
1. ✅ Checks database connection
2. ✅ Detects missing tables
3. ✅ **Creates only missing tables**
4. ✅ Seeds with sample data
5. ✅ Starts FastAPI server

#### **Subsequent Runs**
```bash
./scripts/dev.sh
```

**What happens:**
1. ✅ Checks database connection
2. ✅ **Sees tables exist - does nothing**
3. ✅ Starts FastAPI server immediately

#### **When You Add New Models (Future)**
```bash
# You add a new Pet model
./scripts/dev.sh
```

**What happens:**
1. ✅ Detects existing tables (users)
2. ✅ **Detects new tables (pets)**
3. ✅ **Creates only the new Pet table**
4. ✅ **Preserves existing User data**
5. ✅ Starts FastAPI server

## 🔧 Manual Database Commands

### **Check Database Status**
```bash
python scripts/test_db.py
```
Shows:
- Connection status
- Existing tables and record counts
- Database health

### **Smart Table Creation**
```bash
# Create only missing tables (safe)
python scripts/init_db.py

# Create missing tables + add sample data
python scripts/init_db.py --seed

# Check what would be created (dry run)
python scripts/test_db.py
```

### **Force Recreation (Destructive)**
```bash
# ⚠️ WARNING: This deletes all data!
python scripts/init_db.py --force --seed
```

## 🆕 Adding New Models (Future Workflow)

### **Step 1: Create New Model**
```python
# app/models/pet.py
class Pet(Base):
    __tablename__ = "pets"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    # ... other fields
```

### **Step 2: Update Model Imports**
```python
# app/models/__init__.py
from .user import User, UserRole
from .pet import Pet, PetGender  # Add new import
```

### **Step 3: Run Development Server**
```bash
./scripts/dev.sh
```

**What happens automatically:**
1. ✅ Detects new Pet model
2. ✅ **Creates pets table only**
3. ✅ **Keeps all existing user data**
4. ✅ Logs: "🆕 New tables to create: pets"

### **Step 4: Verify**
```bash
python scripts/test_db.py
```

Shows:
```
✅ users: 4 records (User records)
✅ pets: 0 records (Pet records)
```

## 🏭 Production Environment

### **Production Never Auto-Creates Tables**
```bash
# Production startup
ENVIRONMENT=production uvicorn app.main:app
```

**What happens:**
1. ✅ Checks `ENVIRONMENT=production`
2. ❌ **Skips auto table creation**
3. ✅ Expects tables via migrations
4. ✅ Starts server

### **Production Database Setup**
```bash
# Use Alembic migrations
alembic upgrade head

# Then start server
ENVIRONMENT=production uvicorn app.main:app
```

## 📋 Table Creation Matrix

| Scenario | Tables Dropped | Tables Created | Data Preserved |
|----------|----------------|----------------|----------------|
| **First run** | ❌ No | ✅ All missing | ✅ N/A |
| **Subsequent runs** | ❌ No | ❌ None | ✅ Yes |
| **New model added** | ❌ No | ✅ New only | ✅ Yes |
| **`--force` flag** | ⚠️ **YES** | ✅ All | ❌ **NO** |
| **Production** | ❌ No | ❌ None | ✅ Yes |

## 🔍 Troubleshooting

### **"Table already exists" Error**
This should never happen with our smart system. If it does:
```bash
python scripts/test_db.py  # Check current state
```

### **Missing Tables After Model Changes**
```bash
# Check what's missing
python scripts/init_db.py

# Force detection of new tables
python scripts/init_db.py --seed
```

### **Want to Start Fresh (Development Only)**
```bash
# ⚠️ This deletes all data!
python scripts/init_db.py --force --seed
```

### **Production Table Issues**
```bash
# Use migrations, not scripts
alembic upgrade head
```

## 🎯 Best Practices

### **Development**
- ✅ Use `./scripts/dev.sh` for daily development
- ✅ Use `python scripts/init_db.py` for table updates
- ✅ Use `--force` only when you want to reset data
- ✅ Always check `python scripts/test_db.py` if unsure

### **Production**
- ✅ Always use Alembic migrations
- ✅ Never use development scripts
- ✅ Test migrations in staging first
- ✅ Have database backups before migrations

### **Adding New Models**
- ✅ Create model file
- ✅ Update `app/models/__init__.py`
- ✅ Run `./scripts/dev.sh` (auto-detects new tables)
- ✅ Verify with `python scripts/test_db.py`

## 🚀 Summary

The database management system is designed to be:

- **🧠 Smart**: Only creates what's missing
- **🛡️ Safe**: Never drops data unless explicitly requested
- **🔄 Automatic**: Detects new models and creates tables
- **🏭 Production-Ready**: Uses proper migrations in production
- **👨‍💻 Developer-Friendly**: One command setup and updates

Your data is safe, and adding new models in the future will be seamless! 🎯